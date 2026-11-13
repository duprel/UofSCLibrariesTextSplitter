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
  rm_leading_pages,
  check_status_of_file,
  process_file
)

# def num_cover_pages_in_file(fpath, identifier=None, threshhold=20):
# def rm_leading_pages(in_fpath, out_fpath, identifier, num_pages, leave_original=False):

class TclSignals(QObject):
  result = Signal(dict)
  error = Signal(str)

class TclCheckStatusOfInputFile(QRunnable):

  def __init__(self, fpath, identifier):
    self.fpath = fpath
    self.identifier = identifier
    self.signals = TclSignals()
    super().__init__()

  @Slot()
  def run(self):

    try:
      print(f"checking: {self.fpath}, index: {str(self.identifier)}")
      _path, _id, _result = check_status_of_file(self.fpath, 
                                                 self.identifier)

      # result can be '<' if there are too many words on "cover page"
      #               '?' if the pdf file is not a USC Scholar Commons file
      #               '2' or '1' if we are confident in the result               
      
    except Exception as e:
      self.signals.error.emit(str(e))

    else:
      print(f"TclCheckStatusOfInputFile, file_path: {_path}, result: {_result}")
      self.signals.result.emit({"file_path": _path,
                                "identifier": _id,
                                "result": _result})


class TclProcessInputFile(QRunnable):

  def __init__(self, fpath, outpath, identifier, 
               leave_original=False, backup_extension=None, 
               options={}):
    self.fpath = fpath
    self.outpath = outpath
    self.identifier = identifier
    self.leave_original = leave_original
    self.backup_extension = backup_extension
    self.options = options 
    self.signals = TclSignals()
    super().__init__()

  @Slot()
  def run(self):
    try:
      print(f"Processing file {self.fpath}, index: {str(self.identifier)}, options: {self.options}")
      _path, _id, _result = process_file(self.fpath, 
                                         self.outpath,
                                         self.identifier,
                                         leave_original=self.leave_original,
                                         backup_extension=self.backup_extension,
                                         options=self.options)

      
    except Exception as e:
      self.signals.error.emit(str(e))

    else:
      print(f"TclProcessInputFile, file_path: {_path}, result: {_result}")
      self.signals.result.emit({"file_path": _path,
                                "identifier": _id,
                                "result": _result})

  

__all__ = [ TclCheckStatusOfInputFile,
            TclProcessInputFile,
            TclSignals]





