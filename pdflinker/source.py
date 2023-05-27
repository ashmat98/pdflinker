

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
        self.threads = threads if threads != -1 else multiprocessing.cpu_count()

        self.items = [defaultdict(list) for x in self.patterns]
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
        items = self.process_textpage(page.get_textpage())
        
        if self.ocr:
            items_ocr = self.process_textpage( 
                page.get_textpage_ocr(language=self.language, dpi=300, full=True))
            for items_pattern, items_pattern_ocr in zip(items, items_ocr):
                for idf, rect in items_pattern_ocr:
                    for _, other_rect in items_pattern:
                        if self.area(rect, other_rect) > 0:
                            break
                    else:
                        items_pattern.append((idf, rect))

        return items

    def process_textpage(self, textpage):
        text = textpage.extractText()
        items = []

        for i, (pattern, _) in enumerate(self.patterns):
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
            items.append(items_pattern)
        return items

    def find(self, pbar = None, stop_event=None):
        page_range = list(range(self.start, self.finish))

        if pbar is None:
            pbar = tqdm(total=self.pages)

        if self.threads == 1:
            res = []
            for pi in page_range:
                res.append(self.process_page(pi))
                pbar.update(1)
                
        else:
            pool = multiprocessing.Pool(self.threads)
            res = []

            for element in pool.imap(self.process_page, page_range):
                res.append(element)
                pbar.update(1)
                if stop_event is not None and stop_event.is_set():
                    pool.terminate()
                    pool.close()
                    return

        n_items = [0]*len(self.patterns)
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

        self.find_called = True
        return n_items
        
            
    def sort(self):
        for items, items_source, (_, alignment) in zip(self.items, self.items_source, self.patterns):
            if alignment is Alignment.EXCLUDE:
                continue
            
            x_values = [(0, 10000)]
            for idf, locs in items.items():
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
                items_source[idf] = get_source(locs)

    def create_links(self):
        n_link = [0] * len(self.patterns)
        doc = fitz.open(self.file)

        for i_pattern, (items, items_source) in enumerate(zip(self.items, self.items_source)):
            for idf, locs in items.items():
                source_i = items_source.get(idf, None)
                if source_i is None:
                    continue # excluded pattern

                for i, loc in enumerate(locs):
                    if i != source_i:
                        self._create_link(doc, loc, locs[source_i])
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
