import sys
from PySide6.QtCore import QUrl, Qt
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QFileDialog,
    QWidget,
    QVBoxLayout,
    QGridLayout,
    QFormLayout,
    QPushButton,
    QSlider,
    QLabel,
    QSplitter,
    QHBoxLayout,
    QTabWidget
)
from PySide6.QtGui import QAction
from PySide6.QtMultimedia import QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6 import QtWidgets
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvas
from matplotlib.figure import Figure

# class ParticleDetectionWindow(QMainWindow):

# class ParticleTrackingWindow(QMainWindow):
        
class MainWindow(QMainWindow):
    def __init__(self, page):
        super().__init__()
        self.page = page

        self.determine_page()
        
        

    def determine_page(self):
        if self.page == "particle detection":
            self.particle_detection_window()
        elif self.page == "trajectory tracking":
            self.trajectory_tracking_window()

    def particle_detection_window(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout(self.central_widget)
        self.resize(1200, 500)

        # --- Right Panel (Graphing) ---
        self.main_layout.graph_panel = QWidget()
        self.graph_layout = QVBoxLayout(self.main_layout.graph_panel)
        self.main_layout.addWidget(self.main_layout.graph_panel)
        self.filler_plot()
        self.canvas = FigureCanvas(self.fig)
        self.canvas.setFixedSize(300, 400)
        self.canvas.hide()
        self.graph_layout.addWidget(self.canvas)
        self.sb_button = QPushButton(text="Plot Subpixel Bias", parent=self)
        self.sb_button.setFixedSize(150, 40)
        self.sb_button.clicked.connect(self.show_graph)
        self.graph_layout.addWidget(self.sb_button)
        
        # --- Main splitter ---
        self.splitter = QSplitter(Qt.Horizontal)
        self.main_layout.addWidget(self.splitter)

        # --- Middle Panel (Video Player) ---
        self.main_layout.left_panel = QWidget()
        self.left_layout = QVBoxLayout(self.main_layout.left_panel)
        self.init_video()
        self.splitter.addWidget(self.main_layout.left_panel)

        # --- Media Player Setup ---
        self.player = QMediaPlayer()
        self.player.setVideoOutput(self.video_widget)

        # --- Menu Bar ---
        self.create_menu_bar()

        # --- Status Bar ---
        self.statusBar().showMessage("Ready")

        # --- Right Panel (Tabs) ---
        self.main_layout.right_panel = QWidget()
        self.right_layout = QVBoxLayout(self.main_layout.right_panel)
        self.detection_parameters()
        self.splitter.addWidget(self.main_layout.right_panel)

    def trajectory_tracking_window(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout(self.central_widget)
        self.resize(1200, 500)

        # --- Left Panel (Graphing) ---
        self.main_layout.graph_panel = QWidget()
        self.graph_layout = QVBoxLayout(self.main_layout.graph_panel)
        self.main_layout.addWidget(self.main_layout.graph_panel)
        self.filler_plot()
        self.canvas = FigureCanvas(self.fig)
        self.canvas.setFixedSize(300, 400)
        self.graph_layout.addWidget(self.canvas)
        self.canvas.hide()
        self.sb_button = QPushButton(text="Plot Subpixel Bias", parent=self)
        self.sb_button.setFixedSize(150, 40)
        self.sb_button.clicked.connect(self.show_graph)
        self.graph_layout.addWidget(self.sb_button)

        # --- Main splitter ---
        self.splitter = QSplitter(Qt.Horizontal)
        self.main_layout.addWidget(self.splitter)

        # --- Middle Panel (Video Player) ---
        self.main_layout.left_panel = QWidget()
        self.left_layout = QVBoxLayout(self.main_layout.left_panel)
        self.init_video()
        self.splitter.addWidget(self.main_layout.left_panel)

        # --- Media Player Setup ---
        self.player = QMediaPlayer()
        self.player.setVideoOutput(self.video_widget)

        # --- Menu Bar ---
        self.create_menu_bar()

        # --- Status Bar ---
        self.statusBar().showMessage("Ready")

        # --- Right Panel (Parameters) ---
        self.main_layout.right_panel = QWidget()
        self.right_layout = QVBoxLayout(self.main_layout.right_panel)
        self.trajectory_parameters()
        self.splitter.addWidget(self.main_layout.right_panel)

    def detection_parameters(self):
        self.detection_layout = self.right_layout

        # Mass Slider
        self.mass_label = QLabel("Mass")
        self.mass_slider = QSlider(Qt.Horizontal)
        self.detection_layout.addWidget(self.mass_label)
        self.detection_layout.addWidget(self.mass_slider)

        # Eccentricity Slider
        self.ecc_label = QLabel("Eccentricity")
        self.ecc_slider = QSlider(Qt.Horizontal)
        self.detection_layout.addWidget(self.ecc_label)
        self.detection_layout.addWidget(self.ecc_slider)

        # Size Slider
        self.size_label = QLabel("Size")
        self.size_slider = QSlider(Qt.Horizontal)
        self.detection_layout.addWidget(self.size_label)
        self.detection_layout.addWidget(self.size_slider)

        self.detection_layout.addStretch() # Pushes sliders to the top

    def trajectory_parameters(self):
        self.trajectory_layout = self.right_layout

        # Whatever We Want Slider
        self.mass_label = QLabel("Trajectory things")
        self.mass_slider = QSlider(Qt.Horizontal)
        self.trajectory_layout.addWidget(self.mass_label)
        self.trajectory_layout.addWidget(self.mass_slider)

        # Slider
        self.ecc_label = QLabel("idk")
        self.ecc_slider = QSlider(Qt.Horizontal)
        self.trajectory_layout.addWidget(self.ecc_label)
        self.trajectory_layout.addWidget(self.ecc_slider)

        # Slider
        self.size_label = QLabel("what varibles go here")
        self.size_slider = QSlider(Qt.Horizontal)
        self.trajectory_layout.addWidget(self.size_label)
        self.trajectory_layout.addWidget(self.size_slider)

        self.trajectory_layout.addStretch() # Pushes sliders to the top

    def init_video(self):
        self.video_widget = QVideoWidget(self)
        self.left_layout.addWidget(self.video_widget)

        self.play_pause_button = QPushButton("Play")
        self.play_pause_button.clicked.connect(self.toggle_play_pause)
        self.left_layout.addWidget(self.play_pause_button)
  
    def open_file_dialog(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Open Video", "", "Video Files (*.mp4 *.avi *.mov)")
        if file_name:
            self.player.setSource(QUrl.fromLocalFile(file_name))
            self.player.play()
            self.statusBar().showMessage(f"Playing {file_name}")

    def toggle_play_pause(self):
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
            self.play_pause_button.setText("Pause")
        else:
            self.player.play()
            self.play_pause_button.setText("Play")

    def create_menu_bar(self):
        # import 
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("File")
        import_action = QAction("Import...", self)
        import_action.triggered.connect(self.open_file_dialog)
        file_menu.addAction(import_action)
        # save parameters (doesnt actually work)
        particle_menu = menu_bar.addMenu("Particles")
        save_action = QAction("Save Particle Parameters", self)
        save_action.triggered.connect(self.save_parameters)
        particle_menu.addAction(save_action)
        # reopen parameters
        open_detection_action = QAction("Change Particle Parameters", self)
        open_detection_action.triggered.connect(self.open_detection_page)
        particle_menu.addAction(open_detection_action)
        # go to trajetories
        open_trajectories_action = QAction("Go to Trajectory Tracking", self)
        open_trajectories_action.triggered.connect(self.open_trajectories_page)
        particle_menu.addAction(open_trajectories_action)

    def save_parameters(self):
        pass

    def open_detection_page(self):
        if detection_win.isHidden():
            trajectory_win.hide()
            detection_win.show()

    def open_trajectories_page(self):
        if trajectory_win.isHidden():
            detection_win.hide()
            trajectory_win.show()

    def filler_plot(self):
        self.fig = Figure()
        x = [1, 2, 3, 4, 5]
        y = [1, 4, 9, 16, 25]
        ax = self.fig.add_subplot()
        ax.plot(x, y)

    def show_graph(self):
        self.canvas.show()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    # Sets the style of the gui
    app.setStyle(QtWidgets.QStyleFactory.create("Windows"))
    detection_win = MainWindow("particle detection")
    trajectory_win = MainWindow("trajectory tracking")
    detection_win.show()
    sys.exit(app.exec())
