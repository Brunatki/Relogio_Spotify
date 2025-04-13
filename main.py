import sys
import time
import requests
from io import BytesIO
from PySide6.QtWidgets import QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QSlider
from PySide6.QtGui import QPixmap, QFont, QIcon, QColor, QPalette
from PySide6.QtCore import QTimer, Qt, QPropertyAnimation, QEasingCurve, Property
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
from PIL import Image
from colorthief import ColorThief
import os
from dotenv import load_dotenv

# 🔥 Credenciais de diva

# Carrega as variáveis do .env
load_dotenv()

# Agora você pode acessar as variáveis de ambiente
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")


sp = Spotify(auth_manager=SpotifyOAuth(client_id=CLIENT_ID,
                                       client_secret=CLIENT_SECRET,
                                       redirect_uri=REDIRECT_URI,
                                       scope="user-read-playback-state,user-read-currently-playing,user-modify-playback-state"))

class ColorWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._color = QColor(255, 255, 255)

    def getColor(self):
        return self._color

    def setColor(self, color):
        self._color = color
        palette = self.palette()
        palette.setColor(QPalette.Window, self._color)
        self.setPalette(palette)
        self.setAutoFillBackground(True)

    color = Property(QColor, getColor, setColor)

class SpotifyApp(ColorWidget):
    def __init__(self):
        super().__init__()

        # Config da janela
        self.setWindowTitle("Relógio Spotify - Glam Edition ✨")
        self.setGeometry(100, 100, 320, 600)
        self.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint)
        self.setAutoFillBackground(True)

        # Layout principal
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # Relógio
        self.clock_label = QLabel()
        self.clock_label.setFont(QFont('Arial Black', 28, QFont.Bold))
        self.clock_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.clock_label)

        # Capa do álbum
        self.album_label = QLabel()
        self.album_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.album_label)

        # Nome da música
        self.music_label = QLabel()
        self.music_label.setFont(QFont('Arial Black', 14))
        self.music_label.setAlignment(Qt.AlignCenter)
        self.music_label.setWordWrap(True)
        self.layout.addWidget(self.music_label)

        # Barra de progresso
        self.progress_slider = QSlider(Qt.Horizontal)
        self.progress_slider.setRange(0, 100)
        self.progress_slider.sliderMoved.connect(self.set_position)
        self.layout.addWidget(self.progress_slider)

        # Estilo babadeiro do slider
        self.progress_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 6px;
                background: rgba(0, 0, 0, 0.2);
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: black;
                border: none;
                width: 14px;
                height: 14px;
                margin: -5px 0;
                border-radius: 7px;
            }
            QSlider::sub-page:horizontal {
                background: rgba(0, 0, 0, 0.6);
                border-radius: 3px;
            }
            QSlider::add-page:horizontal {
                background: rgba(255, 255, 255, 0.3);
                border-radius: 3px;
            }
        """)

        # Tempos
        self.time_layout = QHBoxLayout()
        self.start_time_label = QLabel("0:00")
        self.start_time_label.setFont(QFont('Arial Black', 10))
        self.time_layout.addWidget(self.start_time_label)
        self.time_layout.addStretch(1)
        self.end_time_label = QLabel("0:00")
        self.end_time_label.setFont(QFont('Arial Black', 10))
        self.time_layout.addWidget(self.end_time_label)
        self.layout.addLayout(self.time_layout)

        # Botões de controle
        self.buttons_layout = QHBoxLayout()
        self.layout.addLayout(self.buttons_layout)

        def load_icon(name):
            # Caminho para recursos
            if getattr(sys, 'frozen', False):
                base_path = sys._MEIPASS
            else:
                base_path = os.path.abspath(".")
            return QIcon(QPixmap(os.path.join(base_path, 'assets', name)))

        try:
            play_icon = load_icon("play.png")
            pause_icon = load_icon("pause.png")
            next_icon = load_icon("next.png")
            prev_icon = load_icon("prev.png")
        except Exception as e:
            print(f"Erro ao carregar ícones: {e}")

        button_style = """
            QPushButton {
                background-color: transparent;
                border: none;
                min-width: 40px;
                min-height: 40px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 50);
                border-radius: 20px;
            }
        """

        self.prev_button = QPushButton()
        self.prev_button.setIcon(prev_icon)
        self.prev_button.setStyleSheet(button_style)
        self.prev_button.clicked.connect(self.previous_track)
        self.buttons_layout.addWidget(self.prev_button)

        self.play_pause_button = QPushButton()
        self.play_pause_button.setIcon(play_icon)
        self.play_pause_button.setStyleSheet(button_style)
        self.play_pause_button.clicked.connect(self.play_pause_track)
        self.buttons_layout.addWidget(self.play_pause_button)

        self.next_button = QPushButton()
        self.next_button.setIcon(next_icon)
        self.next_button.setStyleSheet(button_style)
        self.next_button.clicked.connect(self.next_track)
        self.buttons_layout.addWidget(self.next_button)

        self.buttons_layout.setAlignment(Qt.AlignCenter)
        self.buttons_layout.setSpacing(10)

        # Timers e animações
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_ui)
        self.timer.start(1000)

        self.color_timer = QTimer()
        self.color_timer.timeout.connect(self.cycle_colors)
        self.color_timer.start(1000)

        self.animation = QPropertyAnimation(self, b"color")
        self.animation.setDuration(800)
        self.animation.setEasingCurve(QEasingCurve.InOutQuad)

        self.colors = []
        self.color_index = 0

        self.update_ui()

    def update_ui(self):
        current_time = time.strftime('%H:%M:%S')
        self.clock_label.setText(current_time)

        track_info = self.get_current_track()

        if track_info and track_info['is_playing']:
            track_name = track_info['item']['name']
            artists = ', '.join([artist['name'] for artist in track_info['item']['artists']])
            self.music_label.setText(f"🎶 {track_name} - {artists}")

            album_image_url = track_info['item']['album']['images'][0]['url']
            self.load_album_image(album_image_url)

            progress_ms = track_info['progress_ms']
            duration_ms = track_info['item']['duration_ms']
            self.progress_slider.setValue(int((progress_ms / duration_ms) * 100))
            self.start_time_label.setText(time.strftime("%M:%S", time.gmtime(progress_ms / 1000)))
            self.end_time_label.setText(time.strftime("%M:%S", time.gmtime(duration_ms / 1000)))
        else:
            self.music_label.setText("Nada tocando... 🎧")
            self.album_label.clear()
            self.progress_slider.setValue(0)
            self.start_time_label.setText("0:00")
            self.end_time_label.setText("0:00")

    def get_current_track(self):
        try:
            return sp.current_user_playing_track()
        except Exception as e:
            print(f"Erro diva: {e}")
            return None

    def load_album_image(self, url):
        response = requests.get(url)
        img_data = Image.open(BytesIO(response.content))
        img_data = img_data.resize((200, 200))

        color_thief = ColorThief(BytesIO(response.content))
        palette = color_thief.get_palette(color_count=6)

        self.colors = [QColor(r, g, b) for r, g, b in palette]
        self.color_index = 0

        # Atualiza capa
        bytes_io = BytesIO()
        img_data.save(bytes_io, format='PNG')
        qpixmap = QPixmap()
        qpixmap.loadFromData(bytes_io.getvalue())
        self.album_label.setPixmap(qpixmap)

    def cycle_colors(self):
        if self.colors:
            color = self.colors[self.color_index]
            self.animation.stop()
            self.animation.setStartValue(self.palette().color(QPalette.Window))
            self.animation.setEndValue(color)
            self.animation.start()

            self.color_index = (self.color_index + 1) % len(self.colors)

    def play_pause_track(self):
        try:
            track_info = self.get_current_track()
            if track_info and track_info['is_playing']:
                sp.pause_playback()
            else:
                sp.start_playback()
        except Exception as e:
            print(f"Erro ao alternar play/pause: {e}")

    def next_track(self):
        try:
            sp.next_track()
        except Exception as e:
            print(f"Erro ao passar música: {e}")

    def previous_track(self):
        try:
            sp.previous_track()
        except Exception as e:
            print(f"Erro ao voltar música: {e}")

    def set_position(self, position):
        track_info = self.get_current_track()
        if track_info:
            duration_ms = track_info['item']['duration_ms']
            new_position_ms = (position / 100) * duration_ms
            sp.seek_track(int(new_position_ms))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SpotifyApp()
    window.show()
    sys.exit(app.exec())
