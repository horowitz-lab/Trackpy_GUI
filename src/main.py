"""
Main Application Controller with Project Management

Description: Main application controller that manages the start screen and project-based workflow.
             Handles switching between start screen and main application windows.
"""

import sys
import os
import platform
import pandas as pd
import shutil
from PySide6.QtWidgets import QApplication, QMainWindow, QStackedWidget, QMessageBox
from PySide6.QtGui import QGuiApplication
from PySide6 import QtWidgets
from src.UI.SSW_StartScreenWindow import SSWStartScreenWindow
from src.UI.DW_DetectionWindow import DWDetectionWindow
from src.UI.LW_LinkingWindow import LWLinkingWindow
from src.utils.ProjectManager import ProjectManager
from src.utils.FileController import FileController
from src.utils.ConfigManager import ConfigManager


class ParticleTrackingAppController(QMainWindow):
    """Main application controller that manages project workflow and window switching."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Particle Tracking GUI")

        # Initialize configuration and managers
        self.project_config = None  # Will be set when project is loaded
        self.project_manager = ProjectManager()
        self.file_controller = (
            None  # Will be initialized when project is loaded
        )

        # Initialize windows
        self.ssw_start_screen_window = None
        self.dw_detection_window = None
        self.lw_linking_window = None

        # Initialize window sizes
        self.win_width = None
        self.win_height = None

        # Create stacked widget for different screens
        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)

        # Show start screen
        self.show_start_screen()

    def show_start_screen(self):
        """Show the start screen for project selection."""
        # Clean up any existing windows
        self.cleanup_windows()

        # Create start screen
        self.ssw_start_screen_window = SSWStartScreenWindow()
        self.ssw_start_screen_window.project_selected.connect(self.on_project_selected)

        self.stacked_widget.addWidget(self.ssw_start_screen_window)
        self.stacked_widget.setCurrentWidget(self.ssw_start_screen_window)

        # Resize the main window to fit the start screen
        self.ssw_start_screen_window.adjustSize()
        self.resize(self.ssw_start_screen_window.size())
        self.center()
        
    def center(self):
        """Center the window on the screen."""
        screen = QGuiApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) / 2
        y = (screen.height() - self.height()) / 2
        self.move(int(x), int(y))

    def on_project_selected(self, project_path):
        """Handle project selection from start screen."""
        # Load the project
        if self.project_manager.load_project(project_path):
            # Initialize project-specific config and file controller
            project_config_path = os.path.join(project_path, "config.ini")
            self.project_config = ConfigManager(project_config_path)
            self.file_controller = FileController(
                self.project_config, project_path
            )

            # Set file controller in particle processing module
            from src.utils import ParticleProcessing

            ParticleProcessing.set_file_controller(self.file_controller)

            # Start the main application workflow
            self.show_particle_detection_window()

            # Check for existing frames
            num_frames = self.file_controller.get_total_frames_count()
            if num_frames > 0:
                self.dw_detection_window.load_existing_frames(num_frames)
            else:
                # If no frames exist, check if video file exists and auto-extract frames
                metadata = self.project_config.get_metadata()
                video_filename = metadata.get("movie_filename", "")
                if video_filename:
                    videos_folder = self.file_controller.videos_folder
                    video_path = os.path.join(videos_folder, video_filename)
                    if os.path.exists(video_path):
                        # Auto-extract frames from video
                        self.dw_detection_window.frame_player.save_video_frames(video_path)
        else:
            print(f"Failed to load project: {project_path}")

    def show_particle_detection_window(self):
        """Show the particle detection window and hide others."""
        # Clean up any existing windows
        self.cleanup_windows(False)

        # Create particle detection window
        self.dw_detection_window = DWDetectionWindow()
        self.dw_detection_window.set_config_manager(self.project_config)
        self.dw_detection_window.set_file_controller(
            self.file_controller
        )

        # Connect signals from particle detection window
        self.dw_detection_window.right_panel.openTrajectoryLinking.connect(
            self.on_next_to_trajectory_linking
        )
        
        # Connect particle analysis to save state for undo
        self.dw_detection_window.right_panel.allParticlesUpdated.connect(
            self._on_particles_updated
        )
        
        # Store reference to main controller in detection window for undo
        self.dw_detection_window.main_controller = self

        # Add to stacked widget
        self.stacked_widget.addWidget(self.dw_detection_window)
        self.stacked_widget.setCurrentWidget(self.dw_detection_window)
        
        # Update undo button state
        if hasattr(self.dw_detection_window, 'update_undo_button_state'):
            self.dw_detection_window.update_undo_button_state()

        # Resize the main window to a fraction of the screen
        available_geometry = QGuiApplication.primaryScreen().availableGeometry()
        self.resize(available_geometry.width() * 0.8, available_geometry.height() * 0.8)
        self.center()

    def show_trajectory_linking_window(self):
        """Show the trajectory linking window and hide others."""
        # Save the current window size and position before switching
        current_size = self.size()
        current_pos = self.pos()
        
        # Clean up any existing windows
        self.cleanup_windows(False)

        # Create trajectory linking window
        self.lw_linking_window = LWLinkingWindow()
        self.lw_linking_window.set_config_manager(self.project_config)
        self.lw_linking_window.set_file_controller(
            self.file_controller
        )

        # Connect signals from trajectory linking window
        self.lw_linking_window.right_panel.goBackToDetection.connect(
            self.on_back_to_particle_detection
        )

        # Add to stacked widget
        self.stacked_widget.addWidget(self.lw_linking_window)
        self.stacked_widget.setCurrentWidget(self.lw_linking_window)

        # Preserve the window size and position from the previous window
        self.resize(current_size)
        self.move(current_pos)

    def on_next_to_trajectory_linking(self):
        """Handle signal to switch from particle detection to trajectory linking."""
        # The particle detection window will handle the "Next" button logic
        # (detecting particles in all frames), then we switch windows
        self.show_trajectory_linking_window()

    def on_back_to_particle_detection(self):
        """Handle signal to switch from trajectory linking back to particle detection."""
        # Save the current window size and position before switching
        current_size = self.size()
        current_pos = self.pos()
        
        # Show particle detection window
        self.show_particle_detection_window()
        
        # Preserve the window size and position
        self.resize(current_size)
        self.move(current_pos)

    def cleanup_windows(self, clear_rb_gallery: bool = True):
        """Clean up existing windows and optionally RB gallery."""
        if clear_rb_gallery:
            self.cleanup_errant_distance_links()

        # Close existing windows
        if self.dw_detection_window:
            self.dw_detection_window.close()
            self.dw_detection_window = None

        if self.lw_linking_window:
            self.lw_linking_window.close()
            self.lw_linking_window = None

    def cleanup_errant_distance_links(self):
        """Delete all files in the rb_gallery folder."""
        if self.file_controller:
            self.file_controller.cleanup_errant_distance_links()

    def closeEvent(self, event):
        """Handle application close event."""
        # Close any open windows but keep generated data on disk
        self.cleanup_windows(False)
        super().closeEvent(event)
    
    def load_spreadsheet_and_config(self, spreadsheet_path: str, config_file_path: str) -> bool:
        """
        Load a spreadsheet and config file to restore GUI state.
        
        This function:
        1. Loads the spreadsheet and replaces all_particles.csv
        2. Loads the config file and updates all parameters
        3. Updates all UI widgets with the new parameters
        4. Sets frame range from config
        5. Refreshes all displays
        
        Parameters
        ----------
        spreadsheet_path : str
            Path to the CSV file containing particle data
        config_file_path : str
            Path to the config.ini file with parameters
            
        Returns
        -------
        bool
            True if successful, False otherwise
        """
        if not self.project_config or not self.file_controller:
            QMessageBox.warning(
                self,
                "No Project Loaded",
                "Please load a project first before importing data."
            )
            return False
        
        try:
            # 1. Load and save the spreadsheet
            if not os.path.exists(spreadsheet_path):
                QMessageBox.warning(
                    self,
                    "File Not Found",
                    f"Spreadsheet file not found: {spreadsheet_path}"
                )
                return False
            
            particles_df = pd.read_csv(spreadsheet_path)
            all_particles_path = os.path.join(self.file_controller.data_folder, "all_particles.csv")
            particles_df.to_csv(all_particles_path, index=False)
            
            # 2. Load and replace the config file FIRST
            if not os.path.exists(config_file_path):
                QMessageBox.warning(
                    self,
                    "File Not Found",
                    f"Config file not found: {config_file_path}"
                )
                return False
            
            # Replace the project config file with the saved config file
            # This MUST happen first before any regeneration
            if self.project_config.config_path:
                # Delete the existing config file first to ensure it's completely replaced
                if os.path.exists(self.project_config.config_path):
                    os.remove(self.project_config.config_path)
                
                # Copy the saved config file to replace the current one
                shutil.copy2(config_file_path, self.project_config.config_path)
                
                # Verify the file was actually copied and has content
                if not os.path.exists(self.project_config.config_path):
                    raise FileNotFoundError(f"Failed to replace config file at {self.project_config.config_path}")
                
                # Verify file sizes match (basic check that copy worked)
                if os.path.getsize(config_file_path) != os.path.getsize(self.project_config.config_path):
                    raise ValueError(f"Config file sizes don't match after copy. Source: {os.path.getsize(config_file_path)}, Dest: {os.path.getsize(self.project_config.config_path)}")
                
                # Clear the old config completely to remove any cached values
                self.project_config.config.clear()
                # Reload the config from the newly replaced file
                # This ensures we're reading the saved config, not the old one
                self.project_config._load_config()
                # Verify config was reloaded by checking a value
                # This ensures the config is valid and has been properly loaded
                test_params = self.project_config.get_detection_params()
                if not test_params:
                    raise ValueError("Config file was not properly loaded after replacement")
            
            # 3. Get all parameters from the reloaded project config
            detection_params = self.project_config.get_detection_params()
            linking_params = self.project_config.get_linking_params()
            frame_range = self.project_config.get_frame_range()
            
            # 4. Update all UI widgets - following the exact same flow as "Find Particles" button
            # Update detection window if it exists
            if self.dw_detection_window:
                # Use centralized refresh function to update all UI elements
                # block_signals=True prevents parameter widgets from overwriting the restored config
                self.dw_detection_window.refresh_detection_ui(
                    particles_df=particles_df,
                    config_manager=self.project_config,
                    frame_range=frame_range,
                    block_signals=True
                )
            
            # Update linking window if it exists
            if self.lw_linking_window:
                # Update config manager
                self.lw_linking_window.set_config_manager(self.project_config)
                
                # Update displays
                self.lw_linking_window._update_parameters_info()
                self.lw_linking_window._update_metadata_display()
            
            QMessageBox.information(
                self,
                "Import Successful",
                "Spreadsheet and config file loaded successfully.\n"
                "All parameters and data have been updated."
            )
            return True
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Import Error",
                f"Error loading spreadsheet and config:\n{str(e)}"
            )
            return False
    
    def save_current_state(self) -> bool:
        """
        Save the current state (spreadsheet and config) to the save folder for undo.
        
        Returns
        -------
        bool
            True if successful, False otherwise
        """
        if not self.project_config or not self.file_controller:
            return False
        
        try:
            # Create save folder in data folder
            save_folder = os.path.join(self.file_controller.data_folder, "save")
            os.makedirs(save_folder, exist_ok=True)
            
            # Save all_particles.csv
            all_particles_path = os.path.join(self.file_controller.data_folder, "all_particles.csv")
            if os.path.exists(all_particles_path):
                save_particles_path = os.path.join(save_folder, "all_particles.csv")
                shutil.copy2(all_particles_path, save_particles_path)
            else:
                # Save empty DataFrame if file doesn't exist
                save_particles_path = os.path.join(save_folder, "all_particles.csv")
                pd.DataFrame().to_csv(save_particles_path, index=False)
            
            # Save config.ini - include current frame range if detection window exists
            save_config_path = os.path.join(save_folder, "config.ini")
            if self.project_config.config_path:
                # Copy the current config file
                shutil.copy2(self.project_config.config_path, save_config_path)
            else:
                # Save current config state
                self.project_config.save(save_config_path)
            
            # Update saved config with current frame range from UI if available
            if self.dw_detection_window and hasattr(self.dw_detection_window, 'right_panel'):
                right_panel = self.dw_detection_window.right_panel
                if hasattr(right_panel, 'start_frame_input'):
                    start_frame = right_panel.start_frame_input.value()
                    end_frame = right_panel.end_frame_input.value()
                    step_frame = right_panel.step_frame_input.value()
                    
                    # Load the saved config and update frame range
                    temp_config = ConfigManager(save_config_path)
                    temp_config.save_frame_range(start_frame, end_frame, step_frame)
                    temp_config.save(save_config_path)
            
            return True
        except Exception as e:
            print(f"Error saving current state: {e}")
            return False
    
    def undo_last_state(self) -> bool:
        """
        Restore the previous state from the save folder.
        
        Returns
        -------
        bool
            True if successful, False otherwise
        """
        if not self.project_config or not self.file_controller:
            return False
        
        save_folder = os.path.join(self.file_controller.data_folder, "save")
        save_particles_path = os.path.join(save_folder, "all_particles.csv")
        save_config_path = os.path.join(save_folder, "config.ini")
        
        # Check if save exists
        if not os.path.exists(save_particles_path) or not os.path.exists(save_config_path):
            return False
        
        # Use the load_spreadsheet_and_config function to restore state
        return self.load_spreadsheet_and_config(save_particles_path, save_config_path)
    
    def has_undo_state(self) -> bool:
        """
        Check if there is a saved state available for undo.
        
        Returns
        -------
        bool
            True if saved state exists, False otherwise
        """
        if not self.file_controller:
            return False
        
        save_folder = os.path.join(self.file_controller.data_folder, "save")
        save_particles_path = os.path.join(save_folder, "all_particles.csv")
        save_config_path = os.path.join(save_folder, "config.ini")
        
        return os.path.exists(save_particles_path) and os.path.exists(save_config_path)
    
    def _on_particles_updated(self):
        """Handle particle analysis completion - update undo button state."""
        # Note: State is saved BEFORE analysis in find_particles()
        # This just updates the button state after analysis completes
        if self.dw_detection_window and hasattr(self.dw_detection_window, 'update_undo_button_state'):
            self.dw_detection_window.update_undo_button_state()


def main():
    """Main application entry point."""
    app = QApplication(sys.argv)

    # Set the application style based on operating system
    system = platform.system()
    available_styles = QtWidgets.QStyleFactory.keys()
    
    if system == "Darwin":  # macOS
        # Don't set a style - let Qt use native macOS styling
        pass
    elif system == "Windows":
        if "Windows" in available_styles:
            app.setStyle(QtWidgets.QStyleFactory.create("Windows"))
        else:
            app.setStyle(QtWidgets.QStyleFactory.create("Fusion"))
    else:
        # Linux or other
        app.setStyle(QtWidgets.QStyleFactory.create("Fusion"))

    # Create and show the main controller
    controller = ParticleTrackingAppController()
    controller.show()

    # Run the application
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
