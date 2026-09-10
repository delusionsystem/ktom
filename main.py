from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QLineEdit, QFrame
from PySide6.QtCore import Qt
from PySide6.QtGui import QIntValidator

class VySkanna(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # CHASSILAYOUT (Responsiv landscape-design utan fasta pixelfönster)
        self.huvud_layout = QHBoxLayout(self)
        self.huvud_layout.setContentsMargins(0, 0, 0, 0)
        self.huvud_layout.setSpacing(0)
        
        # Hämta skärmhöjd för exakt, stram textskalning (4% av H)
        self.H = self.screen().geometry().height()
        self.text_storlek = max(14, int(self.H * 0.04))
        
        # -------------------------------------------------------------
        # VÄNSTER HALVA (50% av W): Rent, fast rutnät för all rådata
        # -------------------------------------------------------------
        self.vanster_chassi = QWidget(self)
        self.vanster_layout = QVBoxLayout(self.vanster_chassi)
        self.vanster_layout.setContentsMargins(20, 20, 20, 20)
        self.vanster_layout.setSpacing(15)
        
        # RAM 1: Scanfönster / Kamerasökare (Låst till 1 pt rätvinklig ram)
        self.scanfinstret = QFrame(self)
        self.scanfinstret.setStyleSheet("border: 1pt solid #444444; background-color: #0d0d0d;")
        
        self.scan_text = QLabel("[ KAMERAN AV - VILOLÄGE ]", self.scanfinstret)
        self.scan_text.setAlignment(Qt.AlignCenter)
        self.scan_text.setStyleSheet(f"font-family: monospace; font-size: {self.text_storlek}px; color: #555555; border: none;")
        
        scan_inner = QVBoxLayout(self.scanfinstret)
        scan_inner.setContentsMargins(0, 0, 0, 0)
        scan_inner.addWidget(self.scan_text)
        self.vanster_layout.addWidget(self.scanfinstret, stretch=35)
        
        # RAM 2: Hårdvarulåst Tuner-fönster (Enbart heltal/siffror)
        self.tuner_pris = QLineEdit(self)
        self.tuner_pris.setPlaceholderText(" ANGE INKÖPSPRIS (SEK)...")
        self.tuner_pris.setValidator(QIntValidator(0, 999999, self)) 
        self.tuner_pris.setStyleSheet(f"""
            QLineEdit {{
                border: 1pt solid #444444; 
                background-color: #222222; 
                color: #ffffff; 
                font-family: monospace; 
                font-size: {int(self.text_storlek * 0.8)}px;
                padding: 8px;
            }}
        """)
        self.vanster_layout.addWidget(self.tuner_pris, stretch=10)
        
        # RAM 3: Datamatris i spalter (INGA SCROLLISTER TILLÅTNA)
        self.matris_ram = QFrame(self)
        self.matris_ram.setStyleSheet("border: 1pt solid #444444; background-color: #151515;")
        
        # Horisontell layout inuti ramen för att fläka ut texten i rena spalter
        self.spalt_layout = QHBoxLayout(self.matris_ram)
        self.spalt_layout.setContentsMargins(10, 10, 10, 10)
        self.spalt_layout.setSpacing(20)
        
        # Spalt 1: Basfakta & Marknadsvärden
        self.spalt_info = QLabel("VÄNTAR PÅ INDATA...", self.matris_ram)
        self.spalt_info.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.spalt_info.setStyleSheet(f"font-family: monospace; font-size: {int(self.text_storlek * 0.75)}px; color: #aaaaaa; border: none;")
        
        # Spalt 2: Den fullständiga låtlistan och unika identifierare (Matrix/Runout)
        self.spalt_latar = QLabel("", self.matris_ram)
        self.spalt_latar.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.spalt_latar.setStyleSheet(f"font-family: monospace; font-size: {int(self.text_storlek * 0.75)}px; color: #888888; border: none;")
        
        self.spalt_layout.addWidget(self.spalt_info, stretch=50)
        self.spalt_layout.addWidget(self.spalt_latar, stretch=50)
        
        self.vanster_layout.addWidget(self.matris_ram, stretch=55)
        
        # -------------------------------------------------------------
        # HÖGER HALVA (50% av W): GIGANTISK TRYCKYTA (Helt orörlig platta)
        # -------------------------------------------------------------
        self.gigantisk_knapp = QFrame(self)
        self.gigantisk_knapp.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #444444, stop:1 #2d2d2d);
            border: 1pt solid #111111; 
            border-left: 1pt solid #3a3a3a;
        """)
        
        self.knapp_text = QLabel("[ SCAN ]", self.gigantisk_knapp)
        self.knapp_text.setAlignment(Qt.AlignCenter)
        self.knapp_text.setStyleSheet(f"font-family: monospace; font-size: {int(self.text_storlek * 1.4)}px; font-weight: bold; color: #ffffff; border: none; background: transparent;")
        
        knapp_layout = QVBoxLayout(self.gigantisk_knapp)
        knapp_layout.setContentsMargins(0, 0, 0, 0)
        knapp_layout.addWidget(self.knapp_text)
        
        # Spika den exakta 50/50-fördelningen i chassit
        self.huvud_layout.addWidget(self.vanster_chassi, stretch=50)
        self.huvud_layout.addWidget(self.gigantisk_knapp, stretch=50)
