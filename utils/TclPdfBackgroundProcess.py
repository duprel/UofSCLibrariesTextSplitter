import sys

from PySide6.QtCore import (
  QObject,
  QRunnable,
  QThreadPool,
  Signal,
  Slot
)

from scholar_commons_pdf import (
  num_cover_pages_in_file,
  rm_leading_pages
)

# def num_cover_pages_in_file(fpath, identifier=None, threshhold=20):
# def rm_leading_pages(in_fpath, out_fpath, identifier, num_pages, leave_original=False):

class TclPdfSignals(QObject):
  result = Signal(dict)
  error = Signal(str)

class TclPdfNumCoverPages(QRunnable):

  def __init__(self, fpath, identifier):
    self.fpath = fpath
    self.identifier = identifier
    self.signals = TclPdfSignals()
    super().__init__()

  @Slot()
  def run(self):

    try:
      print(f"checking: {self.fpath}, index: {str(self.identifier)}")
      _path, _id, _result = num_cover_pages_in_file(self.fpath, 
                                                    self.identifier)

      # result can be '<' if there are too many words on "cover page"
      #               '?' if the pdf file is not a USC Scholar Commons file
      #               '2' or '1' if we are confident in the result               
      
    except Exception as e:
      self.signals.error.emit(str(e))

    else:
      print(f"TclPdfNumCoverPages, file_path: {_path}, result: {_result}")
      self.signals.result.emit({"file_path": _path,
                                "identifier": _id,
                                "result": _result})


class TclPdfRmLeadingPages(QRunnable):

  def __init__(self, fpath, outpath, identifier, num_pages, 
               leave_original=False, backup_extension=None):
    self.fpath = fpath
    self.outpath = outpath
    self.identifier = identifier
    self.num_pages = num_pages
    self.leave_original = leave_original
    self.backup_extension = backup_extension
    self.signals = TclPdfSignals()
    super().__init__()

  @Slot()
  def run(self):

    try:
      print(f"Removing leading {self.num_pages} pages: {self.fpath}, index: {str(self.identifier)}")
      _path, _id, _result = rm_leading_pages(self.fpath, 
                                              self.outpath,
                                              self.identifier,
                                              self.num_pages,
                                              leave_original=self.leave_original,
                                              backup_extension=self.backup_extension)

      # result can be '<' if there are too many words on "cover page"
      #               '?' if the pdf file is not a USC Scholar Commons file
      #               '2' or '1' if we are confident in the result               
      
    except Exception as e:
      self.signals.error.emit(str(e))

    else:
      print(f"TclPdfRmLeadingPages, file_path: {_path}, result: {_result}")
      self.signals.result.emit({"file_path": _path,
                                "identifier": _id,
                                "result": _result})

  






