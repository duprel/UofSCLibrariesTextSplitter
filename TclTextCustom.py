import zipfile
from PySide6.QtWidgets import QMenu, QDialog, QVBoxLayout, QTextEdit
from PySide6.QtGui import QIcon, QAction
from PySide6.QtCore import Qt

from utils.TclInputDirectory import TclInputStatus, TclInput, TclInputDirectory
from utils.TclOutputDirectory import TclOutput, TclOutputDirectory
from ui.widgets.TclInputDirectoryWidget import TclIntegerInputDialog,TclInputDirectoryWidget
from ui.widgets.TclOutputDirectoryWidget import TclOutputDirectoryWidget
from ui.widgets.TclTextViewDialog import TclTextViewDialog

class TclTextInput(TclInput):
  UNCHECKED_ICON = "document-pdf.png"
  STATUS_CONTENT_TAG = "<<STATUSCONTENT>>"
  KNOWN_ICON = "blue-document-number-<<STATUSCONTENT>>.png"
  UNZIP_ICON = "vise-drawer.png"
  UNKNOWN_ICON = "exclamation-red-frame.png"
  SET_ICON = "document-number-<<statausContent>>.png"
  PROCESSED_ICON = "tick.png"

  @classmethod
  def statusContentKey(cls):
    return "num_pages"

  def statusContentIsKnown(self):
    return (self.contents['num_pages'] != '0'
            and self.contents['num_pages'] != '?')

  def statusContentCanBeProcessed(self):
    return (self.contents['num_pages'] != '0'
            and self.contents['num_pages'] != '?')

  def iconForStatus(self):
    if str(self.filename).endswith(".zip"):
      icon = QIcon(str(self.iconDirectory() + "/vise-drawer.png"))
    else:
      match self.status:
        case TclInputStatus.UNCHECKED:
          icon = QIcon(str(self.iconDirectory() + "/document-pdf.png"))
        case TclInputStatus.CHECKED_KNOWN:
          sc = int(self.getStatusContent())
          if sc > 9:
            known_icon_name = "blue-document-number"
          else:
            known_icon_name = f"blue-document-number-{str(sc)}"
          icon = QIcon(str(self.iconDirectory() + f"/{known_icon_name}"))
        case TclInputStatus.CHECKED_UNKNOWN:
          icon = QIcon(str(self.iconDirectory() + "/exclamation-red-frame.png"))
        case TclInputStatus.MANUALLY_SET:
          sc = int(self.getStatusContent())
          if sc > 9:
            set_icon_name = "document-number"
          else:
            set_icon_name = "document-number-{str(sc)}"
          icon = QIcon(str(self.iconDirectory() + f"/{set_icon_name}"))
        case TclInputStatus.PROCESSED:
          icon = QIcon(str(self.iconDirectory() + "/tick.png"))
    return icon

  def setNumCoverPages(self, num_pages):
    self.setStatusContent(num_pages)

  def clearNumCoverPages(self):
    self.clearStatusContent()


class TclTextInputDirectory(TclInputDirectory):
  INPUT_CLASS = TclTextInput

  def getFilesInclusionCheck(self, filename):
    extensions = (".zip",".txt")
    return str(filename).endswith(extensions)


class TclTextOutputDirectory(TclOutputDirectory):
  OUTPUT_CLASS = TclOutput
  GLOB_PATTERN = "*.txt"


class TclTextOutputDirectoryWidget(TclOutputDirectoryWidget):
  OUTPUT_CLASS = TclOutput
  VIEW_DIALOG_CLASS = TclTextViewDialog
  LIST_MODEL_CLASS = TclTextOutputDirectory


#class TclTextNumPagesDialog(TclIntegerInputDialog):
#  DIALOG_TITLE = "Set Number of Pages"
#  INPUT_LABEL = "Number Pages: "
#

class TclArbitraryTextViewDialog(QDialog):

  def __init__(self, parent, settings, text):
    self.text = text
    self.settings = settings
    super().__init__(parent)

    self._view = QTextEdit(self)
    
    v_layout = QVBoxLayout()
    v_layout.addWidget(self._view)
    self.setLayout(v_layout)

    self._view.setText(self.text)
    self.geometry = self.settings.value("view_geometry")
    if self.geometry:
      self.restoreGeometry(self.geometry)
    else:
      self.setGeometry(100,0,800,600)

class TclTextInputDirectoryWidget(TclInputDirectoryWidget):
  INPUT_CLASS = TclTextInput
  VIEW_DIALOG_CLASS = TclTextViewDialog
  LIST_MODEL_CLASS = TclTextInputDirectory
#  SET_INPUT_STATUS_DIALOG_CLASS = TclTextNumPagesDialog
  CHECK_INPUTS_LABEL = "Check Files for Pages"
  PROCESS_INPUTS_LABEL = "Remove Cover Pages"
  RELOAD_INPUTS_LABEL = "Reload"
  PROCESS_INPUT_LABEL = "Split Pages"
  CLEAR_INPUT_LABEL = "Reset Number Pages"
  SET_INPUT_LABEL = "Set Number Pages"
  VIEW_INPUT_LABEL = "View"

  def showContextMenu(self, pos: QPoint):
    index = self.list_view.indexAt(pos)
    self.current_index = index

    menu = QMenu(self)
    if index.isValid():
      item = self.list_model.data(index, Qt.UserRole + 1)
      if str(item.filename).endswith(".zip"):
        menu.addAction(self.unzip_act)
        menu.addAction(self.view_act)
      else:
        menu.addAction(self.view_act)
      menu.exec(self.list_view.viewport().mapToGlobal(pos))

  def iconNameForAction(self, act):
    if act == "UNZIP":
      return "vise-drawer.png"
    else:
      return super().iconNameForAction(act)

  def createActions(self):
    super().createActions()
    self.unzip_act = QAction(self.iconForAction("UNZIP"), "Unzip file")
    self.unzip_act.triggered.connect(self.unzipSelection)

  def viewZippedSelection(self):
    item = self.list_model.data(self.current_index, Qt.UserRole + 1)
    text = ""
    with zipfile.ZipFile(item.filename) as zip:
      for zitem in zip.infolist():
        if not zitem.is_dir() and zitem.filename.lower().endswith(".txt"):
          text += f"{zitem.filename}\n"

    self.dialog = TclArbitraryTextViewDialog(self, self.settings, text)
    self.dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
    self.dialog.exec()

  def viewSelection(self):
    item = self.list_model.data(self.current_index, Qt.UserRole + 1)
    if str(item.filename).endswith('zip'):
      self.viewZippedSelection()
    else:
      super().viewSelection()

  def unzipSelection(self):
    item = self.list_model.data(self.current_index, Qt.UserRole + 1)
    with zipfile.ZipFile(item.filename) as zip:
      for zitem in zip.infolist():
        if not zitem.is_dir() and zitem.filename.lower().endswith(".txt"):
          data = zip.read(zitem)
          if data.startswith((b'\xff\xfe', b'\xfe\xff')):
            text = data.decode('utf-16')
          else:
            text = data.decode('utf-8-sig')
          text = text.replace('\r\n', '\n').replace('\r', '\n')
          fpath = self.settings.value('in_directory') + f"/{zitem.filename}"
          with open(fpath, 'w') as f:
            f.write(text)

    self.reload()


__all__ = [
    TclTextOutputDirectoryWidget,
    TclTextInputDirectoryWidget,
]
