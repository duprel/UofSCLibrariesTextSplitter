from PySide6.QtGui import QIcon

from utils.TclInputDirectory import TclInputStatus, TclInput, TclInputDirectory
from utils.TclOutputDirectory import TclOutput, TclOutputDirectory
from ui.widgets.TclInputDirectoryWidget import TclIntegerInputDialog,TclInputDirectoryWidget
from ui.widgets.TclOutputDirectoryWidget import TclOutputDirectoryWidget
from ui.widgets.TclPdfViewDialog import TclPdfViewDialog

class TclPdfInput(TclInput):
  UNCHECKED_ICON = "document-pdf.png"
  STATUS_CONTENT_TAG = "<<STATUSCONTENT>>"
  KNOWN_ICON = "blue-document-number-<<STATUSCONTENT>>.png"
  UNKNOWN_ICON = "exclamation-red-frame.png"
  SET_ICON = "document-number-<<statausContent>>.png"
  PROCESSED_ICON = "tick.png"

  @classmethod
  def statusContentKey(cls):
    return "num_cover_pages"

  def statusContentIsKnown(self):
    return (self.contents['num_cover_pages'] == '1'
            or self.contents['num_cover_pages'] == '2')

  def statusContentCanBeProcessed(self):
    return (self.contents['num_cover_pages'] == '1'
            or self.contents['num_cover_pages'] == '2')

  def iconForStatus(self):
    match self.status:
      case TclInputStatus.UNCHECKED:
        icon = QIcon(str(self.iconDirectory() + "/document-pdf.png"))
      case TclInputStatus.CHECKED_KNOWN:
        icon = QIcon(str(self.iconDirectory() + f"/blue-document-number-{str(self.getStatusContent())}.png"))
      case TclInputStatus.CHECKED_UNKNOWN:
        icon = QIcon(str(self.iconDirectory() + "/exclamation-red-frame.png"))
      case TclInputStatus.MANUALLY_SET:
        icon = QIcon(str(self.iconDirectory() + f"/document-number-{str(self.getStatusContent())}.png"))
      case TclInputStatus.PROCESSED:
        icon = QIcon(str(self.iconDirectory() + "/tick.png"))
    return icon

  def setNumCoverPages(self, num_pages):
    self.setStatusContent(num_pages)

  def clearNumCoverPages(self):
    self.clearStatusContent()


class TclPdfInputDirectory(TclInputDirectory):
  INPUT_CLASS = TclPdfInput
  GLOB_PATTERN = "*.pdf"


class TclPdfOutputDirectory(TclOutputDirectory):
  OUTPUT_CLASS = TclOutput
  GLOB_PATTERN = "*.pdf"


class TclPdfOutputDirectoryWidget(TclOutputDirectoryWidget):
  OUTPUT_CLASS = TclOutput
  VIEW_DIALOG_CLASS = TclPdfViewDialog
  LIST_MODEL_CLASS = TclPdfOutputDirectory


class TclPdfNumPagesDialog(TclIntegerInputDialog):
  DIALOG_TITLE = "Set Number of Cover Pages"
  INPUT_LABEL = "Num Cover Pages: "


class TclPdfInputDirectoryWidget(TclInputDirectoryWidget):
  INPUT_CLASS = TclPdfInput
  VIEW_DIALOG_CLASS = TclPdfViewDialog
  LIST_MODEL_CLASS = TclPdfInputDirectory
  SET_INPUT_STATUS_DIALOG_CLASS = TclPdfNumPagesDialog
  CHECK_INPUTS_LABEL = "Check Files for Cover Pages"
  PROCESS_INPUTS_LABEL = "Remove Cover Pages"
  RELOAD_INPUTS_LABEL = "Reload"
  PROCESS_INPUT_LABEL = "Remove Cover Pages"
  CLEAR_INPUT_LABEL = "Clear Number Cover Pages"
  SET_INPUT_LABEL = "Set Number Cover Pages"
  VIEW_INPUT_LABEL = "View"


__all__ = [
    TclPdfOutputDirectoryWidget,
    TclPdfInputDirectoryWidget,
]
