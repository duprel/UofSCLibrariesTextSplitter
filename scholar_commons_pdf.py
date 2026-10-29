#!/usr/bin/env python

import builtins
import argparse
import json
import logging
import os
import re
import sys
import traceback
import shutil
from collections import namedtuple
from pathlib import Path
from pypdf import ( PdfReader, PdfWriter )


SearchedTextResult = namedtuple('SearchedTextResult',
                                ['text_label', 'search_label', 'search_text',
                                 'min_searched', 'longest_match', 'match_pos'])

class InconsistentPathing(Exception):
    def __init__(self, input_dir, output_dir):
        super().__init__(f"Either {input_dir} and {output_dir} should both be file paths or both be directory paths.")


class MissingMetaData(Exception):
    def __init__(self, filename):
        super().__init__(f"The file, {filename}, does not have the expected metadata fields.")


logger = logging.getLogger(__name__)
USCSC = "University of South Carolina Scholar Commons"
SNPFAA = "See next page for additional authors"
AUTHORS = "Author(s)"
academic_suffixes = []
academic_suffixes_no_periods = []
min_title_words = 4
min_title_chars = 30

def page_range_to_nums(range_string):
    separator = '-'
    parts = range_string.split(separator)
    ret = None
    if len(parts) == 1:
        start = int(parts[0])
        if start < 1:
            raise ValueError(f"Page number, {parts[0]}, should be greater than zero.")
        ret = [start]
    elif len(parts) == 2:
        start = int(parts[0])
        end = int(parts[1])
        if start < 1 or end < 1:
            raise ValueError(f"Page numbers, {range_string}, should be greater than zero.")
        elif end < start:
            raise ValueError(f"Page range, '{range_string}', should be in ascending order.")
        ret = list(range(start, end+1))
    else:
        raise ValueError(f"Page range, '{range_string}', should be separated by a single hyphen.")

    return ret

def convert_to_zero_based(pages):
    decremented = []
    for num in pages:
        decremented.append(num-1)
    return decremented

def page_str_to_nums(pages_string):
    separator = ','
    pages = []
    pages_valid = re.compile(r"^[0-9,-]+$")
    if not pages_valid.match(pages_string):
        raise ValueError(f"{pages_string} should only contain page numbers separated by commas and hyphens.")
    for part in pages_string.split(separator):
        pages += page_range_to_nums(part)

    pages = convert_to_zero_based(pages)
    return pages

def _get_page_info(reader):
    re_match_word = r'\b\w+\b'
    num_words = []
    num_pages = len(reader.pages)
    page_dimensions = []
    total_words = 0

    for i in range(len(reader.pages)):
        page = reader.pages[i]
        page_dimensions.append(f"{page.mediabox.width},{page.mediabox.height}")
        text = page.extract_text()
        words = re.findall(re_match_word, text)
        num = len(words)

        # We are getting word counts for all pages
        num_words.append(num)

        # But the average number of words per page
        # is going to omit the first and last pages
        # under the assumption that they might be
        # more likely to be a cover page and a
        # partial page.
        if i > 0 and i < num_pages - 1:
            total_words = total_words + num

    return num_words, page_dimensions, total_words//(num_pages - 2)

def get_page_info(in_fpath):
    reader = PdfReader(in_fpath)
    return _get_page_info(reader)

def rm_pages(in_fpath, out_fpath, pages):
    fpath = Path(in_fpath)
    if (fpath.is_file() and
        not fpath.name.startswith('.') and
        fpath.suffix.lower() == '.pdf'):

        if not out_fpath:
            out_fpath = fpath.as_posix()

        logger.debug(f"rm_pages, Removing page(s): {pages}")
        logger.debug(f"rm_pages,             from: {in_fpath}")
        logger.debug(f"rm_pages,   and writing to: {out_fpath}")

        reader = PdfReader(in_fpath)
        writer = PdfWriter()

        for i in range(len(reader.pages)):
            if i not in pages:
                writer.add_page(reader.pages[i])

        with open(out_fpath, 'wb') as f:
            writer.write(f)

        logger.debug(f"rm_pages complete ===================")

def rm_leading_pages(in_fpath, out_fpath, identifier, num_pages,
                     leave_original=False, backup_extension=None):
    def _rm_pages(in_fpath, out_fpath, pages):
        fpath = Path(in_fpath)

        if not out_fpath:
            out_fpath = fpath.as_posix()

        if backup_extension:
            shutil.copy(in_fpath, f"{in_fpath}{backup_extension}")

        message = (f"rm_pages, Removing page(s): {pages}\n"
                   f"rm_pages,             from: {in_fpath}\n"
                   f"rm_pages,   and writing to: {out_fpath}")

        reader = PdfReader(in_fpath)
        writer = PdfWriter()

        for i in range(len(reader.pages)):
            if i not in pages:
                writer.add_page(reader.pages[i])

        with open(out_fpath, 'wb') as f:
            writer.write(f)

        message = message + f"rm_pages complete\n=========="
        return message

    if (int(num_pages) > 9 or
        int(num_pages) < 0):
       return (in_fpath, identifier, f"Document, {in_fpath}, can't be processed, num_pages={num_pages}.")

    message = _rm_pages(in_fpath, out_fpath, list(range(0, int(num_pages))))
    if not leave_original:
        Path(in_fpath).unlink()
    return (in_fpath, identifier, message)

def rm_cover_pages(in_fpath, out_fpath, threshhold, leave_original=False):
    remove_original = False
    def _opath_from_inputs(fpath, out_fpath):
        nm = ''
        if os.path.isdir(out_fpath):
            bname = os.path.basename(fpath)
            nm = os.path.join(os.path.abspath(out_fpath), bname)
        else:
            nm = out_fpath
        return nm

    if not out_fpath:
        out_fpath = in_fpath

    if os.path.isdir(in_fpath):
        if not os.path.isdir(out_fpath):
            raise InconsistentPathing(in_fpath, out_fpath)
        remove_original = not leave_original

    for fpath, num in num_cover_pages(in_fpath, threshhold):
        if num == '1':
            opath = _opath_from_inputs(fpath, out_fpath)
            rm_pages(fpath, opath, [0])
            if remove_original:
                Path(fpath).unlink()
        elif num == '2':
            opath = _opath_from_inputs(fpath, out_fpath)
            rm_pages(fpath, opath, [0, 1])
            if remove_original:
                Path(fpath).unlink()
        elif num == '?':
            logger.error(f"Document, {fpath}, doesn't have the text, '{USCSC}', on the first page. Cannot process.")
        elif num == '<':
            logger.error(f"Document, {fpath}, has too many words on the second page to consider it a cover page. Cannot process.")


def print_meta(in_fpath):
    reader = PdfReader(in_fpath)
    meta = reader.metadata
    print(f"Document meta fields =========")
    print(f"{'title: ':20s}{meta.title}")
    print(f"{'author: ':20s}{meta.author}")
    print(f"{'subject: ':20s}{meta.subject}")
    print(f"{'creator: ':20s}{meta.creator}")
    print(f"{'producer: ':20s}{meta.producer}")
    print(f"{'creation_date: ':20s}{meta.creation_date}")
    print(f"{'modification_date: ':20s}{meta.modification_date}")
    print()


def _get_info(in_fpath, reader):
    words_per_page, page_dims, avg_words_per_internal_page = _get_page_info(reader)
    meta = reader.metadata
    info = {}
    info['authors'] = authors =_get_meta_authors(in_fpath, reader)
    info["name"] = in_fpath.as_posix()
    info["size"] = os.path.getsize(in_fpath)
    info["words_per_page"] = words_per_page
    info["page_dims"] = page_dims
    info["avg_words_per_internal_page"] = avg_words_per_internal_page
    info["meta"] = {}
    info["meta"]["title"] = meta.title
    info["meta"]["author"] = meta.author
    info["meta"]["subject"] = meta.subject
    info["meta"]["creator"] = meta.creator
    info["meta"]["producer"] = meta.producer
    info["meta"]["creation_date"] = meta.creation_date.isoformat()
    info["meta"]["modification_date"] = meta.modification_date.isoformat()
    title = reader.metadata.title
    for index in range(0,3):
        page_label = f"page{index}"
        text = reader.pages[index].extract_text()
        text = text.replace('\n','')
        info[page_label] = get_matches_on_page(page_label,
                                                text,
                                                authors,
                                                title)

    return info

def print_doc_info(in_fpath, threshhold):
    path = Path(in_fpath)
    reader = PdfReader(in_fpath)
    results = _get_document_info(path, reader, threshhold)
    print(json.dumps(results, indent=4, sort_keys=False))

def _get_meta_authors(in_fpath, reader):
    global academic_suffixes, academic_suffixes_no_periods
    meta = reader.metadata
    try:
        if meta.author.find(';') >= 0:
            fnames_w_suffixes = [n.strip() for n in meta.author.split(';')]
        elif meta.author.find(',') >= 0:
            fnames_w_suffixes = [n.strip() for n in meta.author.split(',')]
        elif meta.author.find(' and ') >= 1:
            fnames_w_suffixes = [n.strip() for n in meta.author.split(' and ')]
        else:
            fnames_w_suffixes = [meta.author.strip()]
    except:
        raise MissingMetaData(in_fpath)

    if fnames_w_suffixes[-1].startswith('and '):
        fnames_w_suffixes[-1] = fnames_w_suffixes[-1][4:]
    elif fnames_w_suffixes[-1].startswith(' and '):
        fnames_w_suffixes[-1] = fnames_w_suffixes[-1][5:]

    author_name_parts = []

    def _peel_off_suffixes(parts):
        while (parts[-1] in academic_suffixes or
               parts[-1].replace('.','') in academic_suffixes_no_periods):
            parts = parts[:-1]
        return parts

    for fname in fnames_w_suffixes:
        no_commas = fname.replace(',','')
        fname_parts = no_commas.split()
        fname_parts = _peel_off_suffixes(fname_parts)
        author_name_parts.append(tuple(fname_parts))
    return author_name_parts


def show_matches_on_page(label, page_text, authors, title):
    def _longest_match_of_str(text, match, min):
        longest = -1
        pos = -1
        max = len(match)
        try:
            length = min
            pos = text.index(match[:length])
            while length <= max:
                longest = length
                length = length + 1
                if length <= max:
                    pos = text.index(match[:length])
                else:
                    raise ValueError()
        except ValueError as ve:
            return longest, pos

    indent = "  "
    print(f"{label} ==========")
    print(f"{'title: ':15s}{title}")
    min = 5
    longest_match, position = _longest_match_of_str(page_text, title, min)
    if longest_match > 0:
        print(f"{indent}{'longest_match: ':15s}{title[:longest_match]}")
        print(f"{indent}{'position: ':15s}{position}")
        print(f"{indent}{'min_searched: ':15s}{title[:min]}")
    else:
        print(f"{indent}{'longest_match: ':15s}<none>")
        print(f"{indent}{'position: ':15s}<none>")
        print(f"{indent}{'min_searched: ':15s}{title[:min]}")

    print(f"{'authors: ':15s}{authors}")
    print(f"{'num_authors: ':15s}{len(authors)}")
    for author in authors:
        longest_match = -1
        fn = ' '.join(author)
        print(f"{'author: ':15s}{fn}")
        min = len(fn)
        longest_match, position = _longest_match_of_str(page_text, fn, min)
        if longest_match == -1:
            pattern = r" ([A-Z]\.)([A-Z]\.) "
            replacement = r" \1 \2 "
            new_fn = re.sub(pattern, replacement, fn)
            min = len(new_fn)
            longest_match, position = _longest_match_of_str(page_text, new_fn, min)
        if longest_match > 0:
            print(f"{indent}{'longest_match: ':15s}{fn[:longest_match]}")
            print(f"{indent}{'position:':15s}{position}")
            print(f"{indent}{'min_searched: ':15s}{fn[:min]}")
        else:
            print(f"{indent}{'longest_match: ':15s}<none>")
            print(f"{indent}{'position:':15s}<none>")
            print(f"{indent}{'min_searched: ':15s}{fn[:min]}")

        if longest_match < 0:
            ln = author[-1]
            print(f"{indent}{'author_last: ':15s}{ln}")
            min = len(ln)
            longest_match, position = _longest_match_of_str(page_text, ln, min)
            if longest_match > 0:
                print(f"{indent}{'longest_match: ':15s}{ln[:longest_match]}")
                print(f"{indent}{'position:':15s}{position}")
                print(f"{indent}{'min_searched: ':15s}{ln[:min]}")
            else:
                print(f"{indent}{'longest_match: ':15s}<none>")
                print(f"{indent}{'position:':15s}<none>")
                print(f"{indent}{'min_searched: ':15s}{ln[:min]}")


def get_matches_on_page(page_label, page_text, authors, title):
    def _longest_match_of_str(page_label, search_label, text,
                              match, min, case_insensitive=False, no_space=False):
        longest = -1
        pos = -1
        if case_insensitive:
            if not get_matches_on_page.FOLDED_TEXT:
                get_matches_on_page.FOLDED_TEXT = text.casefold()
            text = get_matches_on_page.FOLDED_TEXT
            if no_space:
                text = text.replace(' ','')
        max = len(match)
        try:
            length = min
            pos = text.index(match[:length])
            while length <= max:
                longest = length
                length = length + 1
                if length <= max:
                    pos = text.index(match[:length])
                else:
                    raise ValueError()
        except ValueError as ve:
            return SearchedTextResult(page_label, search_label, match, min, longest, pos)
        return


    def _find_best_match_of_str(page_label, search_base_label, text, base_search, min):
        longest_match = -1
        results = {}
        search = SIMPLE
        while (longest_match < min and
               search < DONE):
            case_insensitive = False
            no_space = False
            if search == SIMPLE:
                search_label = search_base_label
                search_text = base_search
            elif search == ALL_CAPS:
                search_text = base_search.upper()
                search_label = search_base_label + "_allcaps"
            elif search == NO_CASE:
                case_insensitive = True
                search_text = base_search.casefold()
                search_label = search_base_label + "_nocase"
            elif search == NO_CASE_OR_SPACE:
                case_insensitive = True
                no_space = True
                search_text = base_search.casefold().replace(' ','')
                min = len(search_text)
                search_label = search_base_label + "_allcapsnospace"
            results = _longest_match_of_str(page_label, search_label, text, search_text, min,
                                            case_insensitive, no_space)
            longest_match = results.longest_match
            search = search + 1
        return results

    SIMPLE = 1
    ALL_CAPS = 2
    NO_CASE = 3
    NO_CASE_OR_SPACE = 4
    DONE = 5

    # Set lazy-initialized attribute of function object to hold casefolded text.
    get_matches_on_page.FOLDED_TEXT = ''

    page_results = {}
    page_results['authors'] = authors
    page_results["title"] = title
    min = 30

    search_label = "title_search"
    # I've used the name of the builtin function as a local var, so I have to reference builtins module
    page_results[search_label] = _find_best_match_of_str(page_label, search_label, page_text, title, builtins.min(min, len(title)))

    search_label = "uscsc_search"
    page_results[search_label] = _find_best_match_of_str(page_label, search_label, page_text, USCSC, len(USCSC))

    search_label = "snpfaa_search"
    page_results[search_label] = _find_best_match_of_str(page_label, search_label, page_text, SNPFAA, len(SNPFAA))

    search_label = "authors_label_search"
    page_results[search_label] = _find_best_match_of_str(page_label, search_label, page_text, AUTHORS, len(AUTHORS))

    num_authors = len(authors)
    author_num = 0
    for author in authors:
        author_num = author_num + 1

        fn = ' '.join(author)
        search_label = f"author_search_FN{author_num}of{num_authors}"
        min = len(fn)
        result = _find_best_match_of_str(page_label, search_label, page_text, fn, min)

        # I have seen where the author has multiple initials unseparated in the metadata
        # and they're separated in the document text.
        if result.longest_match == -1:
            pattern = r" ([A-Z]\.)([A-Z]\.) "
            replacement = r" \1 \2 "
            new_fn = re.sub(pattern, replacement, fn)
            if len(new_fn) != len(fn):
                min = len(new_fn)
                page_results[search_label] = _find_best_match_of_str(page_label, search_label, page_text, new_fn, min)
            else:
                page_results[search_label] = result
        else:
            page_results[search_label] = result

        if page_results[search_label].longest_match < 0:
            search_label = f"author_search_LN{author_num}of{num_authors}"
            ln = author[-1]
            min = len(ln)
            page_results[search_label] = _find_best_match_of_str(page_label, search_label, page_text, ln, min)

    return page_results


def find_cover_page_extent(in_fpath):
    reader = PdfReader(in_fpath)
    authors = _get_meta_authors(in_fpath, reader)
    title = reader.metadata.title
    text = reader.pages[0].extract_text().replace('\n','')
    show_matches_on_page("First Page", text, authors, title)
    text = reader.pages[1].extract_text().replace('\n','')
    show_matches_on_page("Second Page", text, authors, title)
    text = reader.pages[2].extract_text().replace('\n','')
    show_matches_on_page("Third Page", text, authors, title)
    text = reader.pages[3].extract_text().replace('\n','')
    show_matches_on_page("Fourth Page", text, authors, title)


def _get_document_info(in_fpath, reader, threshhold):
    info = _get_info(in_fpath, reader)
    info['num_pages'] = len(info['words_per_page'])
    info['num_USC_SC_cover_pages'] = doc_num_cover_pages(in_fpath, info, threshhold)
    return info

def title_appears_on_page(page_results, min_words_match=4, min_match_len=30, case_insensitive=False):
    results = page_results['title_search']

    if results.longest_match == -1:
        return False
    elif results.longest_match < min_match_len:
        return False
    else:
        num_words = len(re.findall(r'\w+', results.search_text[:results.longest_match]))
        if num_words > 1:
            return num_words >= min_words_match
        else:
            return True


def author_names_on_page(page_results, type="FN"):
    # FN: FullName
    # LN: LastName
    matched_searches = set()
    match_text = f"author_search_{type}"
    matched_keys = [k for k in page_results.keys() if k.startswith(match_text)]
    for mk in matched_keys:
        if page_results[mk].longest_match > -1:
            matched_searches.add(mk)

    return matched_searches

def doc_num_cover_pages(in_fpath, info, threshhold=20):
    # A document likely has a two page cover iff
    #  * The title does appear on the first page
    #  * Not all of the authors appear on the first page
    #  * The second page includes either all of the authors
    #    or at least the missing authors
    #  * The title does appear on the third page
    #  * The authors appear on the the third page
    #  * The second page has significantly less text than
    #    the other internal pages.
    cover_pages = "?"
    if (not in_fpath.name.startswith('.') and
        in_fpath.suffix.lower() == '.pdf'):
        uscsc_page0 = info['page0']['uscsc_search'].longest_match == len(USCSC)
        snpfaa_page0 = info['page0']['snpfaa_search'].longest_match == len(SNPFAA)
        authors_label_page1 = info['page1']['authors_label_search'].longest_match == len(AUTHORS)

        if not uscsc_page0:
            cover_pages = '?'
        else:
            if snpfaa_page0 and authors_label_page1:
                if info["avg_words_per_internal_page"]*threshhold/100 < info["words_per_page"][1]:
                    cover_pages = '<'
                else:
                    cover_pages = '2'
            else:
                cover_pages = '1'

    return cover_pages


def pdf_files_in_path(in_path):
    def _is_pdf_file(ipath):
        return (ipath.is_file() and
                not ipath.name.startswith('.') and
                ipath.suffix.lower() == '.pdf')

    ipath  = Path(in_path)
    if ipath.is_dir():
        for fpath in ipath.iterdir():
            if _is_pdf_file(fpath):
                logger.debug(f"Processing {fpath}.")
                yield(fpath)
    if _is_pdf_file(ipath):
        yield(ipath)

def num_cover_pages_in_file(fpath, identifier=None, threshhold=20):
        fpath = Path(fpath)
        reader = PdfReader(fpath)
        try:
          info = _get_document_info(fpath, reader, threshhold)
        except:
          return (fpath, identifier, '?')

        return (fpath, identifier, info['num_USC_SC_cover_pages'])

def num_cover_pages(in_path, threshhold=20):
    def _num_cover_pages(fpath):
        fpath = Path(fpath)
        reader = PdfReader(fpath)
        info = _get_document_info(fpath, reader, threshhold)
        return info['num_USC_SC_cover_pages']

    for fpath in pdf_files_in_path(in_path):
        try:
            num = _num_cover_pages(fpath)
            yield (fpath, num)
        except MissingMetaData:
            logger.debug(f"Skipping file, {in_path}. Unable to extract document meta data.")
            yield (fpath, '?')

def print_num_cover_pages(in_path, threshhold=20):
    for fpath, num in num_cover_pages(in_path, threshhold):
        print(f"{fpath},{num}")

#def get_academic_suffixes(json_path):
#    global academic_suffixes
#    if json_path:
#        with open(json_path) as f:
#            academic_suffixes = json.load(f)
#
#        for suffix in academic_suffixes:
#            academic_suffixes_no_periods.append(suffix.replace('.',''))


def print_version():
    print(f"version: 1.0.4")
    sys.exit(0)

__all__ = [ num_cover_pages_in_file,
            rm_leading_pages ]

def main():
    parser = argparse.ArgumentParser(description="TCL command-line pdf editing tool.")

    parser.add_argument("input", nargs='?', help="The name of the directory or file to process.",
                        type=str)
    parser.add_argument("--verbose",
                        action="store_true")
#    parser.add_argument("--leave-original",
#                        help=("If the input and output are both directories, the default behavior"
#                              " of --rm-cover-pages is to delete the original from the input directory"
#                              " after successfully writing to the output directory. This option"
#                              " overrides that."),
#                        action="store_true")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--rm-pages",
                       help=("Remove list of pages from input and write to output."
                            " The list of page numbers is comma-delimited and may include"
                            " page ranges separated by hyphens. Example: --rm_pages 1,3-6 "),
                        action="store",
                        type=str)
    group.add_argument("--rm-cover-pages",
                       help=(f"Remove cover page(s) from input and write to output. The cover pages"
                             f" are expected to be formatted according to standards of the"
                             f" University of South Carolina Scholar Commons. If the document is not"
                             f" identified as a USC Scholar Commons document it will not be processed."
                             f" If the input is a directory, the output should be too -- and all of the "
                             f" PDF files in the directory will be processed and the results placed in"
                             f" the output directory. If both input and output point to the same file(s)"
                             f" they will be overwritten. If both input and output are provided and"
                             f" point to different directories, upon successful removal of the cover"
                             f" page(s) and writing to the output directory, the original input file in"
                             f" the input directory will be removed. A document is considered to have two"
                             f" cover pages if the first page contains the text '{SNPFAA}' and the second"
                             f" page contains the text '{AUTHORS}'."),
                        action="store_true")
    group.add_argument("--print-doc-info",
                       help=("Print information regarding the input file."),
                       action="store_true")
    group.add_argument("--num-cover-pages",
                       help=("Print the number of cover pages for the <input> PDF file(s). If the input"
                             " points to a directory, print the number of cover pages for each of the"
                             " PDF files stored in the directory. If the document doesn't"
                             " have the 'University of South Carolina Scholar Commons' on the first page"
                             " '?' will be reported. If the document has too many words on the second page"
                             " to be considered a second cover page '<' will be reported. Otherwise, '2'"
                             " or '1' will be reported."),
                       action="store_true")
    group.add_argument("--version",
                       help=("Print script version and exit."),
                       action="store_true")
    parser.add_argument("--cover-page-threshhold",
                        help=("Threshhold percentage value for determining if there is a"
                              " second page as part of the cover page -- cover pages with"
                              " many authors may extend to a second page. If the second page"
                              " of the document has the required text markers and has fewer"
                              " words than this percentage of the average number of words on"
                              " internal document pages, it will be considered part of the"
                              " cover page. Default=20."),
                        action="store",
                        type=int,
                        default='20')
    parser.add_argument("--output",
                        help=("The name of the directory or file to write to. If no output is"
                              " specified, edit the input in place."),
                        action="store",
                        type=str,
                        default=None)
    #parser.add_argument("--academic-suffixes",
    #                    help=("Path to the JSON file containing list of academic suffixes"
    #                          " to pull off of names to reduce to name components."),
    #                    action="store",
    #                    type=str,
    #                    default='')

    args = parser.parse_args()
    if not args.input and not args.version:
        parser.print_help()
        sys.exit(0)


    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    try:
        if args.version:
            print_version()

        args.input = os.path.abspath(args.input)
        #get_academic_suffixes(args.academic_suffixes)
        if args.rm_pages:
            rm_pages(args.input, args.output, page_str_to_nums(args.rm_pages))
        elif args.rm_cover_pages:
            rm_cover_pages(args.input, args.output, args.cover_page_threshhold)
        elif args.print_doc_info:
            print_doc_info(args.input, args.cover_page_threshhold)
        elif args.num_cover_pages:
            print_num_cover_pages(args.input, threshhold=args.cover_page_threshhold)

    except Exception as e:
        traceback.print_exc()

if __name__ == "__main__":
    main()
