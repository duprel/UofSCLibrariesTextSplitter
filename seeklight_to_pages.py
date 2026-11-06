# split seeklight ZIP into 1 txt file per pg
# why: katie needs separate transcript for each img

# the python tools we need
# why: python needs these tools to open ZIPs/check names
import re
import zipfile
from pathlib import Path

# get txt files out ZIP
# why: we need to read transcripts before splitting them up
def read_transcripts(zip_path):

    # keep files here as we read them
    # why: we need place to collect names/txt
    transcripts = []

    # keep track of how big files are
    # why: we DONT want to load too much at once
    total_size = 0

    # open up ZIP
    # why: transcripts are stored inside it
    with zipfile.ZipFile(zip_path) as zip_file:

        # look at each item in ZIP
        # why: 1 download can contain many transcripts
        for item in zip_file.infolist():

            # break up path so we can get filename
            # why: files might be tucked inside folders in ZIP
            parts = item.filename.replace('\\', '/').split('/')

            # skip folders & xtra stuff Macs add
            # why: those arent transcripts so theyre not important here
            if item.is_dir() or '__MACOSX' in parts:
                continue
            # skip hidden stuff too
            # why: those are usually xtra computer files we dont necessarily need
            if any(part.startswith('.') for part in parts):
                continue

            # just keep filename
            # why: finished files all go in 1 folder
            filename = parts[-1]

            # we ONLY need .txt files
            # why: imgs/other files dont need splitting
            if not filename.lower().endswith('.txt'):
                continue

            # add this file to total size
            # why: we need to count whole batch not just 1 file
            total_size += item.file_size
            # stop if theres too much to read at once
            # why: huge batch could use too much memory we dont really want that
            if item.file_size > 64 * 1024 * 1024 or total_size > 512 * 1024 * 1024:
                raise ValueError('This ZIP is too large. Try a smaller batch.')

            # read this file
            # why: we need its contents to find pgs.
            data = zip_file.read(item)

            # check how txt was saved so letters come out right
            # why: txt files can store letters in diff. ways
            if data.startswith((b'\xff\xfe', b'\xfe\xff')):
                text = data.decode('utf-16')
            else:

                text = data.decode('utf-8-sig')

            # stop if we find a character that should NOT be here
            # why: this could mean txt was read wrong way
            if '\x00' in text:
                raise ValueError(f'Check the text encoding in {filename}.')

            # make line breaks match
            # why: diff. computers/devices can save line breaks differently
            text = text.replace('\r\n', '\n').replace('\r', '\n')

            # keep name & txt together
            # why: must know which file each transcript came from
            transcripts.append((filename, text))

    # nothing to work w/ if there are no txt files
    # why: empty batch cant make any pg. files
    if not transcripts:
        raise ValueError('No transcript text files were found in the ZIP.')
    # send list back
    # why: next step needs these files
    return transcripts

# split up 1 transcript
# why: 1 transcript can contain several pgs.
def split_transcript(filename, text):

    # make sure name looks like SCCHR10-0476-002.txt
    # why: we use this name to work out pg. filenames
    if not re.fullmatch(r'SCCHR[0-9]{2}-[0-9]{4}-[0-9]{3}\.txt', filename, re.I):
        raise ValueError(f'Unexpected filename: {filename}')

    # pull box/folder/pg. # out of name
    # why: keep box & folder while counting up pgs.
    box, folder, first_page = filename[:-4].split('-')

    # turn pg. # into # we can add to
    # why: we need to add 1 for each next pg.
    first_page = int(first_page)
    if first_page == 0:
        raise ValueError(f'The page number cannot be 000: {filename}')

    # put pgs. here
    # why: each pg. needs its own piece of txt
    pages = []

    # go line by line & keep spacing
    # why: we can find headers w/o changing pg. txt
    for line in text.splitlines(keepends=True):

        # look for === Page 1 === lines seeklight adds
        # why: these lines tell us where each pg. starts
        header = re.fullmatch(r'===\s+Page\s+([0-9]+)\s+===', line.strip(), re.I)

        if header:
            # grab pg. # from that line
            # why: we need to check pgs. are in order
            page_number = int(header.group(1))

            # check that pgs. go 1 2 3 w/o skipping any
            # why: missing header could give later pgs. wrong names
            if page_number != len(pages) + 1:
                raise ValueError(f'Page headers are missing or out of order in {filename}.')

            # take out xtra blank line like in katies example
            # why: finished files should match katies example
            if pages and pages[-1].endswith('\n\n'):
                pages[-1] = pages[-1][:-1]

            # startnew page & leave out seeklight header
            # why: katie wants pg. txt w/o that added header
            pages.append('')
        # stop if header looks wonky/off
        # why: guessing could split txt in wrong place
        elif re.match(r'===\s*Page\b', line.strip(), re.I):

            raise ValueError(f'A page header looks incomplete in {filename}.')
        # stop if theres txt before page 1 so nothing gets lost
        # why: we dont know which pg. that txt belongs to
        elif not pages:

            if line.strip():
                raise ValueError(f'Text appears before a page header in {filename}.')
        else:

            # add this line to current pg.
            # why: lines between headers belong to same page
            pages[-1] += line

    # stop if we couldnt find where pgs. start
    # why: we cant necessarily safely split pgs. w/o headers
    if not pages:
        raise ValueError(f'No Seeklight page headers were found in {filename}.')

    # match each pg. w/ its new filename
    # why: each saved file needs correct txt inside it
    results = {}
    # go thru pgs. in order
    # why: names need to follow og. pg. order
    for position, page_text in enumerate(pages):

        # start w/ # in filename: 002, 003, 004... etc
        # why: seeklight restarts at 1 but JPEG #s keep going
        original_page = first_page + position
        # pg. #s only have room for 3 digits
        # why: thats filename format we were given
        if original_page > 999:
            raise ValueError(f'The page number would be over 999 in {filename}.')

        # put name back together & keep 0s such as 003
        # why: text filename needs to match JPEG name
        page_name = f'{box}-{folder}-{original_page:03d}.txt'

        # get txt ready to save
        # why: UTF-8s how we are storing letters in new files
        results[page_name] = page_text.encode('utf-8')
    return results

# put all steps together
# why: this runs reading/splitting/saving in order
def convert(zip_path, output_folder):

    transcripts = read_transcripts(zip_path)
    all_pages = {}
    # remember which names we already used
    # why: we need to spot repeated names
    used_names = set()

    # sort out all pgs. before saving them
    # why: bad transcript should be caught before files are written
    for filename, text in transcripts:
        pages = split_transcript(filename, text)
        for page_name, page_text in pages.items():

            # make sure 2 pgs. dont end up w/ same name
            # why: 1 filename cant hold 2 separate pg. files
            if page_name.lower() in used_names:
                raise ValueError(f'Two transcripts would produce {page_name}. Check the grouping.')
            used_names.add(page_name.lower())
            all_pages[page_name] = page_text

    output_folder = Path(output_folder)

    # make folder for finished files if needed
    # why: files need somewhere to go
    output_folder.mkdir(parents=True, exist_ok=True)
    # see whats already in folder
    # why: need to check for files from earlier run
    existing_files = {}
    for file in output_folder.iterdir():
        existing_files[file.name.lower()] = file

    for page_name, page_text in all_pages.items():
        # is this file already here?
        # why: running this again might make same filenames
        existing = existing_files.get(page_name.lower())
        if existing is not None:
            if existing.is_symlink() or not existing.is_file() or existing.name != page_name:
                raise ValueError(f'Choose a new output folder; {page_name} already exists.')
            # DONT replace file if its txts different
            # why: we dont want to erase changes someone made
            if existing.read_bytes() != page_text:
                raise ValueError(f'Choose a new output folder; {page_name} has different text.')

    for page_name, page_text in all_pages.items():
        # skip files we already saved
        # why: identical files dont need saving again
        if page_name.lower() not in existing_files:

            # make new file w/o replacing old 1
            # why: protects file that might already be there
            with (output_folder / page_name).open('xb') as file:
                # save page
                # why: pg. needs to become its own txt file
                file.write(page_text)

    # count how many files we started & ended w/
    # why: final message can tell us what got done
    return len(transcripts), len(all_pages)

# ask where to find ZIP & save pgs.
# why: script needs to know which download to use
def main():

    # find where this python files saved
    # why: short file paths will start from this folder
    script_folder = Path(__file__).resolve().parent

    # ask for ZIP or just tap Enter for example
    # why: we can test example or choose another download
    zip_name = input('Seeklight ZIP [examples/example-seeklight-export.zip]: ').strip().strip('"')
    # ask for folder or tap Enter for finished transcripts
    # why: we can choose where the finished pgs. go
    folder_name = input('Save pages in [finished-transcripts]: ').strip().strip('"')

    # use what was typed or usual choices if left blank
    # why: pressing Enter alone should still work
    zip_path = script_folder / (zip_name or 'examples/example-seeklight-export.zip')
    output_folder = script_folder / (folder_name or 'finished-transcripts')

    try:
        # run steps above
        # why: this starts actual conversion
        objects, pages = convert(zip_path, output_folder)

        # say how it went & where files are
        # why: we need to know it finished/where to look
        print(f'Done: {objects} transcripts became {pages} page files.')
        print(f'Saved in: {output_folder}')
    # say what went wrong if it didnt work (if nothing went wrong...HOORAY!)
    # why: error message helps us figure out what to fix
    except (OSError, ValueError, zipfile.BadZipFile, RuntimeError) as error:
        print(f'Could not finish: {error}')
        return 1
    return 0

# start here when we hit Run
# why: python needs to know which step to start w/
if __name__ == '__main__':

    raise SystemExit(main())
