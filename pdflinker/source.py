

import fitz
import os
import re
from tqdm import tqdm
from collections import defaultdict
import multiprocessing
from .utils import Alignment, remove_capturing_pattern
import logging

logger = logging.getLogger()

class PdfLinker:
    def __init__(self, file, patterns, pages=-1, start=0, ocr=False, language="eng", threads=1):
        self.file = file
        doc = fitz.open(file)
        self.start = start
        if pages == -1:
            self.finish = doc.page_count
        else:
            self.finish = min(doc.page_count,
                self.start + pages)
        self.pages = self.finish - self.start
        
        
        self.ocr = ocr
        self.language="eng"

        self.patterns = patterns
        for pattern, pattern_for_source, alignment in self.patterns:
            assert isinstance(pattern, str)
            assert isinstance(pattern_for_source, str)
            assert isinstance(alignment, Alignment)

        self.threads = threads if threads != -1 else multiprocessing.cpu_count()

        # for each pattern, for each identifier gives list of (page_index, rectangle) pair
        self.items = [defaultdict(list) for x in self.patterns]
        self.items_for_source = [defaultdict(list) for x in self.patterns]
        self.items_source = [dict() for x in self.patterns]

        self.rectangles = defaultdict(list)
        self.find_called = False
        logger.debug("PdfLinker.__init__ finished")



    @staticmethod
    def area(a , b=None):
        if b is None:
            b = a
        dx = min(a.x1, b.x1) - max(a.x0, b.x0)
        dy = min(a.y1, b.y1) - max(a.y0, b.y0)
        if (dx>=0) and (dy>=0):
            return dx*dy
        return 0

    @staticmethod
    def _get_identifier(pattern, text):
        res = re.findall(pattern, text)
        assert len(res) == 1
        res = res[0]
        if type(res) is str:
            res = (res,)
        return tuple(re.sub(r"\s", r"", x) for x in res)

    
    def process_page(self, page_number):
        doc = fitz.open(self.file)
        page = doc.load_page(page_number)
        items, items_for_source = self.process_textpage(page.get_textpage())
        
        def add_non_overlapping(items, items_ocr):
            for items_pattern, items_pattern_ocr in zip(items, items_ocr):
                for idf, rect in items_pattern_ocr:
                    for _, other_rect in items_pattern:
                        if self.area(rect, other_rect) > 0:
                            break
                    else:
                        items_pattern.append((idf, rect))

        if self.ocr:
            items_ocr, items_for_source_ocr = self.process_textpage( 
                page.get_textpage_ocr(language=self.language, dpi=300, full=True))
            
            add_non_overlapping(items, items_ocr)
            add_non_overlapping(items_for_source, items_for_source_ocr)
            
        return items, items_for_source

    def process_textpage(self, textpage):
        text = textpage.extractText()
        items = []
        items_for_source = []


        def process_for_pattern(text, pattern):
            items_pattern = []
            pattern_nocap = remove_capturing_pattern(pattern)
            try:
                item_expressions = set(re.findall(pattern_nocap, text))
            except re.error as e:
                print(f"Problem with regex {pattern_nocap}")
                print(e)
                raise e
            for expr in item_expressions:
                identifier = PdfLinker._get_identifier(pattern, expr)
                for rect in textpage.search(expr, quads=0):
                    items_pattern.append(
                        (identifier, rect)
                    )
            return items_pattern
            
        for i, (pattern, pattern_for_source, _) in enumerate(self.patterns):
            items_pattern = process_for_pattern(text, pattern)
            if pattern_for_source == pattern:
                items_pattern_for_source = items_pattern
            else:
                items_pattern_for_source = process_for_pattern(text, pattern_for_source)
            
            items.append(items_pattern)
            items_for_source.append(items_pattern_for_source)
        
        return items, items_for_source

    @staticmethod
    def overlap_ratio(rect, other_rect):
        area = PdfLinker.area
        return area(rect, other_rect) / (1e-8 +  min(area(rect), area(other_rect)))
    
    def find(self, pbar = None, stop_event=None):
        page_range = list(range(self.start, self.finish))

        if pbar is None:
            pbar = tqdm(total=self.pages)
        
        pbar.update(0)

        res = []
        if self.threads == 1:
            for page_index in page_range:
                res.append(self.process_page(page_index))
                pbar.update(1)
                if stop_event is not None and stop_event.is_set():
                    return
                
        else:
            pool = multiprocessing.Pool(self.threads)
            for element in pool.imap(self.process_page, page_range):
                res.append(element)
                pbar.update(1)
                if stop_event is not None and stop_event.is_set():
                    pool.terminate()
                    pool.close()
                    return

        # number of items found per pattern
        n_items = [0]*len(self.patterns)

        def clean_overlapping_items(page_index, items):
            items_new = []
            for idf, rect in items:
                # if page != page_index:
                #     continue
                for other_rect in self.rectangles[page_index]:
                    if self.overlap_ratio(rect, other_rect) > 0.3:
                        # current item overlaps with one of previous items, thus discarded 
                        break
                else:
                    self.rectangles[page_index].append(rect)
                    items_new.append((idf, rect))
            return items_new
            
        ## old code
        if False:
            for pi, items in zip(page_range, res):
                for i_pattern, items_pattern in enumerate(items):
                    for idf, rect in items_pattern:
                        for other_rect in self.rectangles[pi]:
                            if self.area(rect, other_rect) > 0.3 * min(self.area(rect), self.area(other_rect)):
                                break
                        else:
                            self.rectangles[pi].append(rect)
                            self.items[i_pattern][idf].append((pi, rect))
                            n_items[i_pattern] += 1

        #####

        for page_index, (items, items_for_source) in zip(page_range, res):
            for i_pattern, (items_p, items_for_source_p) in enumerate(zip(items, items_for_source)):
                for idf, rect in clean_overlapping_items(page_index, items_p):
                    self.items[i_pattern][idf].append((page_index, rect))
                    n_items[i_pattern] += 1

                if self.patterns[i_pattern][0] == self.patterns[i_pattern][1]:
                    continue
                
                for idf, rect in clean_overlapping_items(page_index, items_for_source_p):
                    self.items_for_source[i_pattern][idf].append((page_index, rect))


        self.find_called = True
        return n_items
        
            
    def sort(self):
        for i_pattern, (pattern, pattern_for_source, alignment) in enumerate(self.patterns):
            if alignment is Alignment.EXCLUDE:
                continue

            if pattern == pattern_for_source:
                items = self.items[i_pattern]
            else:
                items = self.items_for_source[i_pattern]

            items_source = self.items_source[i_pattern]

            # sort found items per pattern
            # also store horisontal coordinates of items in `x_values`
            x_values = [(0, 10000)]
            for idf, locs in items.items(): # locs = [(page_index, rectangle), ...]
                items[idf] = sorted(locs, key=lambda x:(x[0], x[1].y0))
                x_values += [(rect.x0, rect.x1) for _, rect in locs]

            pos = min(len(x_values),int(len(items) * 1.1)) # x_limit position

            if alignment in [Alignment.RIGHT,Alignment.RIGHT_END]:
                x_values = sorted(x_values, key=lambda x: x[1], reverse=True) # sort by x1
                x_limit = x_values[pos][1] # take x1

                def get_source(locs):
                    at_end = (alignment is Alignment.RIGHT_END)
                    iterator = list(enumerate(locs))
                    iterator = (iterator[::-1] if at_end else iterator)[:4]
                    for i, (_, rect) in iterator:
                        if rect.x1 > x_limit:
                            return i
                    return len(locs)-1 if at_end else 0

            elif alignment in [Alignment.LEFT, Alignment.LEFT_END]:
                x_values = sorted(x_values, key=lambda x: x[0], reverse=False) # sort by x0
                x_limit = x_values[pos][0] # take x0

                def get_source(locs):
                    at_end = (alignment is Alignment.LEFT_END)
                    iterator = list(enumerate(locs))
                    iterator = (iterator[::-1] if at_end else iterator)[:4]
                    for i, (_, rect) in iterator:
                        if rect.x0 < x_limit:
                            return i
                    return len(locs)-1 if at_end else 0
                    
            else: # Alignment.END or Alignment.None or something else
                def get_source(locs):
                    return len(locs)-1 if alignment is Alignment.END else 0
            
                    
            for idf, locs in items.items():
                source_i = get_source(locs)
                page, rect = items[idf][source_i]
                items_source[idf] = (page, rect)

    def create_links(self):
        n_link = [0] * len(self.patterns)
        doc = fitz.open(self.file)

        for i_pattern, (items, items_source) in enumerate(zip(self.items, self.items_source)):
            for idf, locs in items.items():
                page_to, rect_to = items_source.get(idf, (None, None))

                if page_to is None:
                    continue # excluded pattern

                for i, (page_from, rect_from) in enumerate(locs):
                    if page_from == page_to and self.overlap_ratio(rect_from, rect_to) > 0.3:
                        # source and destination matches
                        continue
                    
                    self._create_link(doc, (page_from, rect_from), (page_to, rect_to))
                    n_link[i_pattern] += 1

        return doc, n_link
    
    @staticmethod
    def _create_link(doc, _from, _to):
        from_page = doc.load_page(_from[0])
        from_rect = _from[1]

        to_page, to_rect = _to

        link={ #makealinkfromit
            "kind": fitz.LINK_GOTO,
            "from": from_rect,
            "to": fitz.Point(0, max(0, to_rect.y0 - 10)),
            "page": to_page,
            "name" : "Ashot's link"
        }
        from_page.insert_link(link)

    def remove_links(self):
        doc = fitz.open(self.file)
        for i_page in range(doc.page_count):
            page = doc.load_page(i_page)
            for link_dict in page.get_links():
                if "fitz" in link_dict["id"]:
                    page.delete_link({"xref" : link_dict["xref"]})
        return doc
    
    # def save(self, output):
    #     self.doc.save(output)
