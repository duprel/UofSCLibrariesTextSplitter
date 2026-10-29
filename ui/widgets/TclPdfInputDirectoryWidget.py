import os, sys, time
from pathlib import Path
from PySide6.QtWidgets import (QApplication, QDialog, QLabel, QWidget, QListWidget,
    QDialogButtonBox, QGroupBox, QRadioButton, QListWidgetItem, QListView,
    QProgressBar, QLineEdit, QPushButton, QTextEdit, QMenu, QSpinBox,
    QComboBox, QFileDialog, QHBoxLayout, QVBoxLayout, QMainWindow, QStatusBar)
from PySide6.QtCore import (QCoreApplication, Qt, Signal, QSettings, QStandardPaths,
                            QSize, QPoint)
from PySide6.QtGui import QAction, QIcon
from .TclPdfSettingsDialog import PdfSettingsDialog
from utils.TclPdfInputDirectory import (TclPdfInputStatus, TclPdfInputDirectory, 
                                              CheckNumCoverPages, RmLeadingPages)
from .TclPdfViewDialog import TclPdfViewDialog

ui_dir = Path(__file__).resolve().parents[1]

document_icon_path  = str(ui_dir/"resources"/"icons"/"document-pdf.png")
pencil_icon_path    = str(ui_dir/"resources"/"icons"/"pencil.png")
eraser_icon_path    = str(ui_dir/"resources"/"icons"/"eraser.png")
lightning_icon_path = str(ui_dir/"resources"/"icons"/"lightning.png")


class NumPagesDialog(QDialog):
  numCoverPagesSelected = Signal(int)

  def __init__(self, parent=None):
    self.num_cover_pages = None
    super().__init__(parent)
    self.setModal(True)
    self.initializeUI()

  def initializeUI(self):
    self.setWindowTitle("Set Number of Cover Pages")
    v_layout = QVBoxLayout()
    h_layout = QHBoxLayout()
    label = QLabel("Num Cover Pages: ")
    h_layout.addWidget(label)
    spinbox = QSpinBox()

    spinbox.setMinimum(0)
    spinbox.setMaximum(9)
    spinbox.lineEdit().setReadOnly(True)
    spinbox.valueChanged.connect(self.value_changed)
    h_layout.addWidget(spinbox)

    buttons = (QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel)
    button_box = QDialogButtonBox(buttons)
    button_box.accepted.connect(self.accept)
    button_box.rejected.connect(self.reject)

    v_layout.addLayout(h_layout)
    v_layout.addWidget(button_box)
    self.setLayout(v_layout)

  def value_changed(self, value):
    self.num_cover_pages = value

  def accept(self): 
    self.numCoverPagesSelected.emit(self.num_cover_pages)
    self.done(QDialog.DialogCode.Accepted)
    super().accept()

  def reject(self): 
    self.done(QDialog.DialogCode.Rejected)
    super().reject()


class TclPdfInputDirectoryWidget(QWidget):

  def __init__(self, settings):
    super().__init__()
    self.current_index = None
    self.async_operations = False
    self.settings = settings
    self.initializeUI()

  def initializeUI(self):
    """Set up the application's GUI."""

    self.setUpMainWindow()
    self.createActions()
    self.checkButtonEnabling()
    self.show()
    
  def setUpMainWindow(self):
    if self.settings.value("in_directory", None):
      input_dir_text = str(self.settings.value("in_directory"))
    else:
      input_dir_text = "<<Go to settings to set the PDF input directory>>"

    self.input_label = QLabel(f"Input Directory: {input_dir_text}")

    self.list_view = QListView()
    self.list_model = TclPdfInputDirectory(self.settings)
    self.list_view.setModel(self.list_model)
    self.list_view.setContextMenuPolicy(Qt.CustomContextMenu)
    self.list_view.customContextMenuRequested.connect(self.showContextMenu)

    message_label = QLabel(f"Messages:")
    self.text_edit = QTextEdit()
    self.text_edit.setAcceptRichText(False)
    self.text_edit.setReadOnly(True)

    self.progress_bar = QProgressBar()
    self.progress_bar.setValue(0)

    vbox = QVBoxLayout()
    vbox.addWidget(self.input_label)
#    vbox.addWidget(self.list_widget)
    vbox.addWidget(self.list_view)
    vbox.addWidget(message_label)
    vbox.addWidget(self.text_edit)
    vbox.addWidget(self.progress_bar)

    self.check_cover_pages_button = QPushButton('Check Files for Cover Pages')
    self.check_cover_pages_button.clicked.connect(self.checkFilesForCoverPages)
    self.rem_cover_pages_button = QPushButton('Remove Cover Pages')
    self.rem_cover_pages_button.clicked.connect(self.removeCoverPages)
    self.reload_pdfs_button = QPushButton('Reload')
    self.reload_pdfs_button.clicked.connect(self.reloadPdfs)

    hbox = QHBoxLayout()
    hbox.addWidget(self.check_cover_pages_button)
    hbox.addWidget(self.rem_cover_pages_button)
    hbox.addWidget(self.reload_pdfs_button)
    vbox.addLayout(hbox)

    self.setLayout(vbox)

  def unsetAsyncOperations(self):
    #print("async_operations False")
    self.async_operations = False
    self.checkButtonEnabling()

  def setAsyncOperations(self):
    #print("async_operations True")
    self.async_operations = True
    self.checkButtonEnabling()

  def checkButtonEnabling(self):
    row_count = self.list_model.rowCount()
    check_cover_pages_enabled = False
    rem_cover_pages_enabled = False

    if not self.async_operations:
      for row in range(row_count):
        index = self.list_model.index(row,0)
        item = self.list_model.data(index, Qt.UserRole + 1)

        match item.status:
          case TclPdfInputStatus.UNCHECKED:
            check_cover_pages_enabled = True
          case TclPdfInputStatus.CHECKED_KNOWN | TclPdfInputStatus.MANUALLY_SET:
            rem_cover_pages_enabled = True

        if check_cover_pages_enabled and rem_cover_pages_enabled:
          break

    self.check_cover_pages_button.setEnabled(check_cover_pages_enabled)
    self.rem_cover_pages_button.setEnabled(rem_cover_pages_enabled)
        
  def checkFilesForCoverPages(self):
    if not self.async_operations:
      #print("checkFilesForCoverPages")
      self.setAsyncOperations()
      self.progress_bar.setValue(0)
      self.checkNumCoverPages = CheckNumCoverPages(self.list_model)
      self.checkNumCoverPages.progress.connect(self.showProgress)
      self.checkNumCoverPages.finished.connect(self.setNumPagesFor)
      self.checkNumCoverPages.processFiles()
    #else:
    #  print("BLOCKED ==========================")

  def showProgress(self, percent_complete):
    self.progress_bar.setValue(percent_complete)
    if percent_complete >= 100:
      self.unsetAsyncOperations()
      self.progress_bar.setValue(0)

  def setNumPagesFor(self, result):
    message = f"Checked '{str(result["file_path"])}'\n"
    message += f"Result: {result['result']} pages\n"
    message += "=========="
    self.text_edit.append(message)
    row_specifier = result["identifier"]
    num_pages = result["result"]
    item = self.list_model.data(row_specifier, Qt.UserRole + 1)
    if num_pages == '1' or num_pages == '2':
      item.status = TclPdfInputStatus.CHECKED_KNOWN
    else:
      item.status = TclPdfInputStatus.CHECKED_UNKNOWN
    item.num_cover_pages = num_pages
    self.list_model.dataChanged.emit(row_specifier, row_specifier, [])
    self.checkButtonEnabling()

  def clearNumPagesFor(self, result):
    row_specifier = result["identifier"]
    item = self.list_model.data(row_specifier, Qt.UserRole + 1)
    item.status = TclPdfInputStatus.UNCHECKED
    item.num_cover_pages = None
    self.list_model.dataChanged.emit(row_specifier, row_specifier, [])
    self.checkButtonEnabling()
    
  def setProcessedFor(self, result):
    row_specifier = result["identifier"]
    item = self.list_model.data(row_specifier, Qt.UserRole + 1)
    item.status = TclPdfInputStatus.PROCESSED
    item.num_cover_pages = None
    self.list_model.dataChanged.emit(row_specifier, row_specifier, [])
    self.checkButtonEnabling()
    
  def showFinishedFor(self, result):
    self.text_edit.append(result["result"])
    if self.settings.value("retention_policy") == "Retain":
      self.clearNumPagesFor(result)
    else:
      self.setProcessedFor(result)
    self.checkButtonEnabling()

  def removeCoverPages(self):
    if not self.async_operations:
      #print("removeCoverPages")
      self.setAsyncOperations()
      self.progress_bar.setValue(0)
      self.removeCoverPages = RmLeadingPages(self.list_model, self.settings)
      self.removeCoverPages.progress.connect(self.showProgress)
      self.removeCoverPages.finished.connect(self.showFinishedFor)
      self.removeCoverPages.processFiles()
    #else:
    #  print("BLOCKED ==========================")

  def reloadPdfs(self):
    input_dir_text = str(self.settings.value("in_directory"))
    self.input_label.setText(f"Input Directory: {input_dir_text}")
    self.list_model.reload()
    self.checkButtonEnabling()

  def showContextMenu(self, pos: QPoint):
    index = self.list_view.indexAt(pos)
    self.current_index = index

    menu = QMenu(self)
    if index.isValid():
      item = self.list_model.data(index, Qt.UserRole + 1)
      #menu = item.contextMenu(self)
      menu.addAction(self.view_act)
      menu.addAction(self.set_num_pages_act)
      if item.num_cover_pages is not None:
        menu.addAction(self.clear_num_pages_act)
      menu.exec(self.list_view.viewport().mapToGlobal(pos))

  def createActions(self):
    self.view_act = QAction(QIcon(document_icon_path), "View")
    self.view_act.triggered.connect(self.viewSelection)
    self.list_view.doubleClicked.connect(self.itemDoubleClicked)

    self.set_num_pages_act = QAction(QIcon(pencil_icon_path), "Set Number Cover Pages")
    self.set_num_pages_act.triggered.connect(self.setNbrPagesSelection)

    self.clear_num_pages_act = QAction(QIcon(eraser_icon_path), "Clear Number Cover Pages")
    self.clear_num_pages_act.triggered.connect(self.clearSelection)

    self.remove_cover_pages_act = QAction(QIcon(lightning_icon_path), "Remove Cover Pages")
    self.remove_cover_pages_act.triggered.connect(self.removeCoverPagesSelection)

  def itemDoubleClicked( self, index):
    self.current_index = index
    self.viewSelection()

  def viewSelection(self):
    item = self.list_model.data(self.current_index, Qt.UserRole + 1)
    self.dialog = TclPdfViewDialog(self, self.settings, str(item.filename))
    self.dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
    self.dialog.exec()

  def setNbrPagesSelection(self, num_pages):
    print("setNbrPagesSelection")
    self.dialog = NumPagesDialog(self)
    #self.dialog.setModal(True)
    self.dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
    self.dialog.setFixedSize(300,150)
    self.dialog.numCoverPagesSelected.connect(self.setNumCoverPages)
    self.dialog.exec()

  def setNumCoverPages(self, num_pages):
    if self.current_index:
      item = self.list_model.data(self.current_index, Qt.UserRole + 1)
      item.num_cover_pages = num_pages
      item.status = TclPdfInputStatus.MANUALLY_SET
      self.list_model.dataChanged.emit(self.current_index, 
                                       self.current_index,
                                       [Qt.DecorationRole])
      self.checkButtonEnabling()

      
  def clearSelection(self):
    if self.current_index:
      item = self.list_model.data(self.current_index, Qt.UserRole + 1)
      item.num_cover_pages = None
      item.status = TclPdfInputStatus.UNCHECKED
      self.list_model.dataChanged.emit(self.current_index, 
                                       self.current_index,
                                       [Qt.DecorationRole])
      self.checkButtonEnabling()
    
  def removeCoverPagesSelection(self):
    print("removeCoverPagesSelection")
  
  def editSettingsDialog(self):
    dialog = PdfSettingsDialog(self, self.settings)
    dialog.pdfSettingsAccepted.connect(self.setSettings)
    dialog.exec()


__all__ = [
  'TclPdfInputDirectoryWidget'
  ]
