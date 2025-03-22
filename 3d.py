import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
from matplotlib.widgets import Button

class AdvancedCNCPlotter:
    def __init__(self):
        # Motor konumları (gizli)
        self.M1 = (0, 300)
        self.M2 = (400, 300)
        self.M3 = (200, 0)
        
        # Sistem durumu
        self.pen_down = False
        self.current_pos = (0, 0)
        self.draw_color = '#27ae60'
        self.travel_color = '#e74c3c'
        
        # Geometrik hesaplamalar
        self.calculate_geometry()
        
        # Grafik başlatma
        plt.ion()
        self.fig, self.ax = self.initialize_plot()
        self.setup_ui()
        self.update_connections(*self.incenter)

    def calculate_geometry(self):
        """Geometrik parametreleri hesapla"""
        points = [self.M1, self.M2, self.M3]
        a = np.linalg.norm(np.array(points[1]) - np.array(points[2]))
        b = np.linalg.norm(np.array(points[0]) - np.array(points[2]))
        c = np.linalg.norm(np.array(points[0]) - np.array(points[1]))
        
        s = (a + b + c) / 2
        self.area = np.sqrt(s * (s - a) * (s - b) * (s - c))
        self.radius = self.area / s
        
        self.incenter = (
            (a*self.M1[0] + b*self.M2[0] + c*self.M3[0]) / (a + b + c),
            (a*self.M1[1] + b*self.M2[1] + c*self.M3[1]) / (a + b + c)
        )
        self.current_pos = self.incenter

    def initialize_plot(self):
        """Grafik arayüzünü başlat"""
        fig, ax = plt.subplots(figsize=(14, 10))
        
        # Üçgen çerçeve (motorlar gizli)
        ax.plot([self.M1[0], self.M2[0]], [self.M1[1], self.M2[1]], 'k-', alpha=0.5)
        ax.plot([self.M2[0], self.M3[0]], [self.M2[1], self.M3[1]], 'k-', alpha=0.5)
        ax.plot([self.M3[0], self.M1[0]], [self.M3[1], self.M1[1]], 'k-', alpha=0.5)
        
        # Güvenli bölge
        self.safe_circle = plt.Circle(
            self.incenter, self.radius,
            color='#f1c40f', alpha=0.15, label='Güvenli Bölge'
        )
        ax.add_artist(self.safe_circle)
        
        # Bilgi paneli
        info_text = (f"Güvenli Bölge Yarıçapı: {self.radius:.1f} cm\n"
                     f"İç Merkez: ({self.incenter[0]:.1f}, {self.incenter[1]:.1f})")
        ax.text(10, 50, info_text, fontsize=12,
                bbox=dict(facecolor='white', alpha=0.85))
        
        # Grafik ayarları
        ax.set_title("3 Motorlu CNC Simülasyonu", fontsize=16, pad=20)
        ax.set_xlabel("X Ekseni (cm)", fontsize=12)
        ax.set_ylabel("Y Ekseni (cm)", fontsize=12)
        ax.grid(True, linestyle='--', alpha=0.7)
        ax.set_xlim(-50, 450)
        ax.set_ylim(-50, 350)
        ax.set_aspect('equal', adjustable='datalim')
        
        return fig, ax

    def setup_ui(self):
        """Kullanıcı arayüzünü kur"""
        # Bağlantı çizgileri
        self.conn_lines = [
            self.ax.plot([], [], '--', alpha=0.3, linewidth=10.5)[0]
            for _ in range(3)
        ]
        
        # Kontrol butonu
        self.btn_restart = Button(
            plt.axes([0.4, 0.02, 0.2, 0.06]),
            'Tekrar Başlat',
            color='#2ecc71',
            hovercolor='#27ae60'
        )
        self.btn_restart.on_clicked(self.restart_simulation)
        
        # Lejant (motorlar gizli)
        from matplotlib.lines import Line2D
        legend_elements = [
            Line2D([0], [0], color='#27ae60', lw=2, label='Kalem Aşağı (M03)'),
            Line2D([0], [0], color='#2980b9', lw=2, label='Kalem Yukarı (M05)'),
            Line2D([0], [0], color='#f1c40f', lw=2, label='Güvenli Bölge')
        ]
        self.ax.legend(handles=legend_elements, loc='upper right', fontsize=10)

    def update_connections(self, x, y):
        """Motor bağlantılarını güncelle"""
        for i, (mx, my) in enumerate([self.M1, self.M2, self.M3]):
            self.conn_lines[i].set_data([mx, x], [my, y])

    def process_gcode(self, filename):
        """G-code dosyasını işle"""
        try:
            with open(filename, 'r') as f:
                print(f"{filename} işleniyor...")
                for line_num, line in enumerate(f, 1):
                    self.process_line(line.strip(), line_num)
                print("İşlem tamamlandı")
        except Exception as e:
            print(f"Hata: {str(e)}")

    def process_line(self, line, line_num):
        """G-code komutunu işle"""
        line = line.split(';')[0].strip()
        if not line:
            return

        parts = line.split()
        cmd = parts[0].upper()
        
        try:
            {
                'G00': lambda: self.move(parts[1:], False),
                'G01': lambda: self.move(parts[1:], True),
                'M03': lambda: setattr(self, 'pen_down', True),
                'M05': lambda: setattr(self, 'pen_down', False),
                'G28': lambda: self.move_to(*self.incenter, False)
            }.get(cmd, lambda: print(f"Bilinmeyen komut: {cmd}"))()
        except Exception as e:
            print(f"Satır {line_num} hatası: {str(e)}")

    def move(self, args, draw):
        """Hareket komutunu işle"""
        x = self.parse_coord(args, 'X')
        y = self.parse_coord(args, 'Y')
        self.move_to(x or self.current_pos[0], 
                    y or self.current_pos[1], draw)

    def parse_coord(self, args, axis):
        """Koordinat değerini çözümle"""
        for arg in args:
            if arg.upper().startswith(axis):
                try:
                    return float(arg[1:].replace(',', '.'))
                except ValueError:
                    raise ValueError(f"Geçersiz {axis} değeri: {arg[1:]}")
        return None

    def move_to(self, x, y, draw):
        """Yeni pozisyona hareket et"""
        # Güvenlik kontrolü
        if not self.is_safe(x, y):
            raise ValueError(f"Güvenli bölge dışı! ({x:.1f}, {y:.1f})")
        
        # Çizim parametreleri
        color = self.draw_color if draw and self.pen_down else self.travel_color
        style = '-' if draw and self.pen_down else ':'
        
        # Çizimi gerçekleştir
        self.ax.plot(
            [self.current_pos[0], x],
            [self.current_pos[1], y],
            color=color,
            linestyle=style,
            linewidth=2 if draw else 1
        )
        
        # Güncellemeler
        self.current_pos = (x, y)
        self.update_connections(x, y)
        plt.pause(0.901)

    def is_safe(self, x, y):
        """Güvenlik kontrolü"""
        return np.hypot(x-self.incenter[0], y-self.incenter[1]) <= self.radius

    def restart_simulation(self, event):
        """Simülasyonu sıfırla (EKSİK METOD EKLENDİ)"""
        # Çizimleri temizle (ilk 6 sabit çizimi koru)
        while len(self.ax.lines) > 6:
            self.ax.lines[-1].remove()
        
        # Parametreleri sıfırla
        self.current_pos = self.incenter
        self.pen_down = False
        self.draw_color = '#27ae60'
        self.update_connections(*self.incenter)
        
        # Grafiği yenile
        self.fig.canvas.draw_idle()
        plt.pause(0.1)
        
        # G-code'u yeniden yükle
        if Path("ornek.ngc").exists():
            self.process_gcode("ornek.ngc")

    def run(self):
        """Uygulamayı başlat"""
        plt.show(block=True)

if __name__ == "__main__":
    simulator = AdvancedCNCPlotter()
    
    # G-code dosyasını yükle
    gcode_file = "ornek.ngc"
    if Path(gcode_file).exists():
        simulator.process_gcode(gcode_file)
    else:
        print(f"Uyarı: {gcode_file} bulunamadı!")
    
    simulator.run()
