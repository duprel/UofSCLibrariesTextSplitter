import os, sys, time
from pathlib import Path
from PySide6.QtWidgets import (QApplication, QDialog, QLabel, QWidget, QListWidget,
    QDialogButtonBox, QGroupBox, QRadioButton, QListWidgetItem, QListView, QTabWidget,
    QProgressBar, QLineEdit, QPushButton, QTextEdit, QMenu, QSpinBox,
    QComboBox, QFileDialog, QHBoxLayout, QVBoxLayout, QMainWindow, QStatusBar)
from PySide6.QtCore import (QCoreApplication, Qt, Signal, QSettings, QStandardPaths,
                            QSize, QPoint)
from PySide6.QtGui import QAction, QIcon
from ui.widgets.TclPdfSettingsDialog import PdfSettings, PdfSettingsDialog
from ui.widgets.TclPdfViewDialog import TclPdfViewDialog
from ui.widgets.TclPdfInputDirectoryWidget import TclPdfInputDirectoryWidget
from ui.widgets.TclPdfOutputDirectoryWidget import TclPdfOutputDirectoryWidget

def get_asset_path(relative_path):
  try:
    basepath = sys._MEIPASS
  except AttributeError:
    basepath = os.path.abspath(".")

  return os.path.join(basepath, relative_path)


style_sheet = """
    QProgressBar{
        background-color: #C0C6CA;
        color: #FFFFFF;
        border: 1px solid grey;
        padding: 3px;
        height: 15px;
        text-align: center;
    }

    QProgressBar::chunk{
        background: #538DB8;
        width: 5px;
        margin: 0.5px
    }
"""

try:
  from ctypes import windll

  mmyappid = "edu.sc.tcl.pdfcoverpageremover.20260916"
  windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
except:
  pass

class MainWindow(QMainWindow):

  def __init__(self):
    super().__init__()
    self.initializeSettings()
    self.initializeUI()

  def initializeSettings(self):
    self.settings = QSettings()
    size = self.settings.value("window_size", QSize(650,650))
    position = self.settings.value("window_position", QPoint(100,100))
    geometry = self.settings.value("window_geometry", None)
    self.setWindowTitle("PDF Cover Page Removal")
    self.resize(size)
    self.move(position)
    if geometry:
      self.restoreGeometry(geometry)

  def closeEvent(self, ev):
    self.settings.setValue("window_position", self.pos())
    self.settings.setValue("window_size", self.size())
    self.settings.setValue("window_geometry", self.saveGeometry())
    self.saveSettings()
    super().closeEvent(ev)

  def initializeUI(self):
    """Set up the application's GUI."""

    self.setUpMainWindow()
    self.createActions()
    self.createMenu()
    self.show()
    
  def setUpMainWindow(self):
    vbox = QVBoxLayout()
    
    self.tab_widget = QTabWidget()
    self.tab_input_dir = TclPdfInputDirectoryWidget(self.settings)
    self.tab_output_dir = TclPdfOutputDirectoryWidget(self.settings)
    self.tab_widget.addTab(self.tab_input_dir, "Input Directory")
    self.tab_widget.addTab(self.tab_output_dir, "Output Directory")
  
    self.tab_widget.currentChanged.connect(self.tabChanged)
    vbox.addWidget(self.tab_widget)
    self.central_widget = QWidget()
    self.central_widget.setLayout(vbox)
    self.setCentralWidget(self.central_widget)

    self.setStatusBar(QStatusBar())

  def createActions(self):
    """Create the application's menu actions."""
    self.settings_act = QAction(QIcon(get_asset_path("ui/resources/images/gear.png")), "Settings")
    self.settings_act.setShortcut("Ctrl+S")
    self.settings_act.setStatusTip("Set input directory, output directory, and backup policy")
    self.settings_act.triggered.connect(self.editSettingsDialog)

    self.quit_act = QAction(QIcon(get_asset_path("ui/resources/images/exit.png")), "Quit")
    self.quit_act.setShortcut("Ctrl+Q")
    self.quit_act.setStatusTip("Quit program")
    self.quit_act.triggered.connect(self.close)

  def createMenu(self):
    """Create the application's menu bar."""
    self.menuBar().setNativeMenuBar(False)

    # Create File menu and add actions 
    settings_menu = self.menuBar().addMenu("Edit")
    settings_menu.addAction(self.settings_act)

    app_menu = self.menuBar().addMenu("App")
    app_menu.addAction(self.quit_act)

  def editSettingsDialog(self):
    dialog = PdfSettingsDialog(self, self.settings)
    dialog.pdfSettingsAccepted.connect(self.setSettings)
    dialog.exec()

  def setSettings(self, ev):
    settings_tuple = ev
    print(settings_tuple)
    prev_in_directory = self.settings.value("in_directory")
    prev_out_directory = self.settings.value("out_directory")
    self.settings.setValue("in_directory", settings_tuple.in_directory)
    self.settings.setValue("out_directory", settings_tuple.out_directory)
    self.settings.setValue("overwrite_policy", settings_tuple.overwrite_policy)
    self.settings.setValue("backup_extension", settings_tuple.backup_extension)
    self.settings.setValue("retention_policy", settings_tuple.retention_policy)
    self.saveSettings()
    if settings_tuple.in_directory != prev_in_directory:
      self.tab_input_dir.reloadPdfs()
    if settings_tuple.out_directory != prev_out_directory:
      self.tab_output_dir.reloadPdfs()

  def saveSettings(self):
    self.settings.sync()
    print(f"settings file: {self.settings.fileName()}")

  def tabChanged(self, index):
    if index == 1:
      self.tab_output_dir.reloadPdfs()


  #def moveEvent(self, e):
  #  print(self.pos())
  #  super(MainWindow, self).moveEvent(e)

#basedir = os.path.dirname(__file__)

if __name__ == '__main__':
  QCoreApplication.setOrganizationName("University of South Carolina Libraries")
  QCoreApplication.setOrganizationDomain("sc.edu/libraries")
  QCoreApplication.setApplicationName("PDF Cover Page Remover")
  app = QApplication(sys.argv)
  app.setWindowIcon(QIcon(get_asset_path("ui/resources/images/gamecock_head_and_neck_icon_rgb_rose.svg")))
  #app.setWindowIcon(QIcon(os.path.join(basedir,
  #                                     "gamecock_head_and_neck_icon_rgb_rose.svg")))
  app.setStyleSheet(style_sheet)
  app.setAttribute(
    Qt.ApplicationAttribute.AA_DontShowIconsInMenus, False)
  window = MainWindow()
  sys.exit(app.exec())

