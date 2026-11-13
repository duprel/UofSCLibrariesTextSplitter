from pathlib import Path
from PySide6.QtWidgets import (QDialog, QLabel, QWidget, QDialogButtonBox, QListView,
                               QProgressBar, QPushButton, QTextEdit, QMenu, QSpinBox, 
                               QHBoxLayout, QVBoxLayout)
from PySide6.QtCore import (Qt, Signal, QPoint)
from PySide6.QtGui import QAction, QIcon
from .TclDirSettingsDialog import TclDirSettingsDialog
from utils.TclInputDirectory import (TclInputStatus, TclInputDirectory, 
                                     TclCheckStatusOfInputFiles, TclProcessInputFiles)


class TclIntegerInputDialog(QDialog):
  valueSelected = Signal(int)
  DIALOG_TITLE = ""
  INPUT_LABEL = ""

  def __init__(self, parent=None):
    self.integerValue = None
    super().__init__(parent)
    self.setModal(True)
    self.initializeUI()

  def initializeUI(self):
    self.setWindowTitle(self.DIALOG_TITLE)
    v_layout = QVBoxLayout()
    h_layout = QHBoxLayout()
    label = QLabel(self.INPUT_LABEL)
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
    self.integerValue = value

  def accept(self): 
    self.valueSelected.emit(self.integerValue)
    self.done(QDialog.DialogCode.Accepted)
    super().accept()

  def reject(self): 
    self.done(QDialog.DialogCode.Rejected)
    super().reject()


class TclInputDirectoryWidget(QWidget):
  INPUT_CLASS = None
  VIEW_DIALOG_CLASS = None
  SET_INPUT_STATUS_DIALOG_CLASS = None

  CHECK_INPUTS_LABEL = ""
  PROCESS_INPUTS_LABEL = ""
  RELOAD_INPUTS_LABEL = "Reload"
  PROCESS_INPUT_LABEL = ""
  CLEAR_INPUT_LABEL = ""
  SET_INPUT_LABEL = ""
  VIEW_INPUT_LABEL = "View"

  VIEW_ICON = "document-pdf.png"
  SET_ICON = "pencil.png"
  CLEAR_ICON = "eraser.png"
  PROCESS_ICON = "lightning.png"

  @classmethod
  def iconDirectory(cls):
    return "ui/resources/icons"

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
      input_dir_text = "<<Go to settings to set the input directory>>"

    self.input_label = QLabel(f"Input Directory: {input_dir_text}")

    self.list_view = QListView()
    self.list_model = self.LIST_MODEL_CLASS(self.settings, self.INPUT_CLASS)
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
    vbox.addWidget(self.list_view)
    vbox.addWidget(message_label)
    vbox.addWidget(self.text_edit)
    vbox.addWidget(self.progress_bar)

    self.check_input_status_button = QPushButton(self.CHECK_INPUTS_LABEL)
    self.check_input_status_button.clicked.connect(self.checkStatusOfInputFiles)
    
    self.process_input_files_button = QPushButton(self.PROCESS_INPUTS_LABEL)
    self.process_input_files_button.clicked.connect(self.processInputFiles)
    
    self.reload_input_files_button = QPushButton(self.RELOAD_INPUTS_LABEL)
    self.reload_input_files_button.clicked.connect(self.reloadInputFiles)

    hbox = QHBoxLayout()
    hbox.addWidget(self.check_input_status_button)
    hbox.addWidget(self.process_input_files_button)
    hbox.addWidget(self.reload_input_files_button)
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
    check_input_status_enabled = False
    process_input_files_enabled = False

    if not self.async_operations:

      for row in range(row_count):
        index = self.list_model.index(row,0)
        item = self.list_model.data(index, Qt.UserRole + 1)

        match item.status:
          case TclInputStatus.UNCHECKED:
            check_input_status_enabled = True
          case TclInputStatus.CHECKED_KNOWN | TclInputStatus.MANUALLY_SET:
            process_input_files_enabled = True

        if check_input_status_enabled and process_input_files_enabled:
          break

    self.check_input_status_button.setEnabled(check_input_status_enabled)
    self.process_input_files_button.setEnabled(process_input_files_enabled)
        
  def checkStatusOfInputFiles(self):
    if not self.async_operations:
      #print("checkFilesForCoverPages")
      self.setAsyncOperations()
      self.progress_bar.setValue(0)
      self.checkStatusOfInputFiles = TclCheckStatusOfInputFiles(self.list_model)
      self.checkStatusOfInputFiles.progress.connect(self.showProgress)
      self.checkStatusOfInputFiles.finished.connect(self.setStatusFor)
      self.checkStatusOfInputFiles.processFiles()
    #else:
    #  print("BLOCKED ==========================")

  def showProgress(self, percent_complete):
    self.progress_bar.setValue(percent_complete)
    if percent_complete >= 100:
      self.unsetAsyncOperations()
      self.progress_bar.setValue(0)

  def setStatusFor(self, result):
    message = f"Checked '{str(result["file_path"])}'\n"
    message += f"Result: {result['result']} pages\n"
    message += "=========="
    self.text_edit.append(message)
    row_specifier = result["identifier"]
    status_content = result["result"]
    item = self.list_model.data(row_specifier, Qt.UserRole + 1)
    item.setStatusContent(status_content)
    if item.statusContentIsKnown():
      item.status = TclInputStatus.CHECKED_KNOWN
    else:
      item.status = TclInputStatus.CHECKED_UNKNOWN
    self.list_model.dataChanged.emit(row_specifier, row_specifier, [])
    self.checkButtonEnabling()

  def clearStatusContentFor(self, result):
    row_specifier = result["identifier"]
    item = self.list_model.data(row_specifier, Qt.UserRole + 1)
    item.clearStatusContent()
    item.status = TclInputStatus.UNCHECKED
    self.list_model.dataChanged.emit(row_specifier, row_specifier, [])
    self.checkButtonEnabling()
    
  def setProcessedFor(self, result):
    row_specifier = result["identifier"]
    item = self.list_model.data(row_specifier, Qt.UserRole + 1)
    item.clearStatusContent()
    item.status = TclInputStatus.PROCESSED
    self.list_model.dataChanged.emit(row_specifier, row_specifier, [])
    self.checkButtonEnabling()
    
  def showFinishedFor(self, result):
    self.text_edit.append(result["result"])
    if self.settings.value("retention_policy") == "Retain":
      self.clearStatusContentFor(result)
    else:
      self.setProcessedFor(result)
    self.checkButtonEnabling()

  def processInputFiles(self):
    if not self.async_operations:
      #print("removeCoverPages")
      self.setAsyncOperations()
      self.progress_bar.setValue(0)
      self.processInputs = TclProcessInputFiles(self.list_model, self.settings)
      self.processInputs.progress.connect(self.showProgress)
      self.processInputs.finished.connect(self.showFinishedFor)
      self.processInputs.processFiles()
    #else:
    #  print("BLOCKED ==========================")

  def reloadInputFiles(self):
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
      menu.addAction(self.set_input_status_act)
      if item.getStatusContent() is not None:
        menu.addAction(self.clear_input_status_act)
      menu.exec(self.list_view.viewport().mapToGlobal(pos))

  def iconNameForAction(self, act):
    icon_name = ''
    match act:
      case "DOCUMENT":
        icon_name = self.INPUT_CLASS.DOCUMENT_ICON
      case "SET":
        icon_name = self.INPUT_CLASS.EDIT_ICON
      case "CLEAR":
        icon_name = self.INPUT_CLASS.CLEAR_ICON
      case "PROCESS":
        icon_name = self.INPUT_CLASS.PROCESS_ICON

    return icon_name
        
  def iconForAction(self, act):
    return QIcon(self.iconDirectory() + "/" + self.iconNameForAction(act))

  
  def createActions(self):
    self.view_act = QAction(self.iconForAction("DOCUMENT"), self.VIEW_INPUT_LABEL)
    self.view_act.triggered.connect(self.viewSelection)
    self.list_view.doubleClicked.connect(self.itemDoubleClicked)

    self.set_input_status_act = QAction(self.iconForAction("SET"), self.SET_INPUT_LABEL)
    self.set_input_status_act.triggered.connect(self.invokeSetInputStatus)

    self.clear_input_status_act = QAction(self.iconForAction("CLEAR"), self.CLEAR_INPUT_LABEL)
    self.clear_input_status_act.triggered.connect(self.clearInputStatus)

    self.process_act = QAction(self.iconForAction("PROCESS"), self.PROCESS_INPUT_LABEL)
    self.process_act.triggered.connect(self.processInput)

  def itemDoubleClicked( self, index):
    self.current_index = index
    self.viewSelection()

  def viewSelection(self):
    item = self.list_model.data(self.current_index, Qt.UserRole + 1)
    self.dialog = self.VIEW_DIALOG_CLASS(self, self.settings, str(item.filename))
    self.dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
    self.dialog.exec()

  def invokeSetInputStatus(self, val):
    print("invokeSetInputStatus")
    self.dialog = self.SET_INPUT_STATUS_DIALOG_CLASS(self)
    #self.dialog.setModal(True)
    self.dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
    self.dialog.setFixedSize(300,150)
    self.dialog.valueSelected.connect(self.setInputStatus)
    self.dialog.exec()

  def setInputStatus(self, val):
    if self.current_index:
      item = self.list_model.data(self.current_index, Qt.UserRole + 1)
      item.setStatusContent(val)
      item.status = TclInputStatus.MANUALLY_SET
      self.list_model.dataChanged.emit(self.current_index, 
                                       self.current_index,
                                       [Qt.DecorationRole])
      self.checkButtonEnabling()

      
  def clearInputStatus(self):
    if self.current_index:
      item = self.list_model.data(self.current_index, Qt.UserRole + 1)
      item.clearStatusContent()
      item.status = TclInputStatus.UNCHECKED
      self.list_model.dataChanged.emit(self.current_index, 
                                       self.current_index,
                                       [Qt.DecorationRole])
      self.checkButtonEnabling()
    
  def processInput(self):
    print("processInput")
  
  def editSettingsDialog(self):
    dialog = TclDirSettingsDialog(self, self.settings)
    dialog.dirSettingsAccepted.connect(self.setSettings)
    dialog.exec()


__all__ = [
  'TclInputDirectoryWidget',
  'TclIntegerInputDialog',
  ]
