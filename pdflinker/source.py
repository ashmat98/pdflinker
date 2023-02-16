

import fitz
import os
import re
from tqdm import tqdm
from collections import defaultdict
import multiprocessing
from .utils import Alignment, remove_capturing_pattern

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

        self.ocr = ocr
        self.language="eng"
        self.patterns = patterns
        self.threads = threads if threads != -1 else multiprocessing.cpu_count()

        self.items = [defaultdict(list) for x in self.patterns]
        self.items_source = [dict() for x in self.patterns]



    @staticmethod
    def area(a , b):  # returns None if rectangles don't intersect
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


            item_expressions = set(re.findall(pattern_nocap, text))
            for expr in item_expressions:
                identifier = PdfLinker._get_identifier(pattern, expr)
                for rect in textpage.search(expr, quads=0):
                    items_pattern.append(
                        (identifier, rect)
                    )
            items.append(items_pattern)
        return items

    def find(self):
        page_range = list(range(self.start, self.finish))

        if self.threads == 1:
            res = []
            for pi in tqdm(page_range):
                res.append(self.process_page(pi))
                
        else:
            pool = multiprocessing.Pool(self.threads)
            res = list(tqdm(
                pool.imap(self.process_page, page_range), 
                total=len(page_range)))
        
        n_items = [0]*len(self.patterns)
        for pi, items in zip(page_range, res):
            for i_pattern, items_pattern in enumerate(items):
                for idf, rect in items_pattern:
                    self.items[i_pattern][idf].append((pi, rect))
                    n_items[i_pattern] += 1

        return n_items
        
            
    def sort(self):
        for items, items_source, (_, alignment) in zip(self.items, self.items_source, self.patterns):
            x_values = []
            for idf, locs in items.items():
                items[idf] = sorted(locs, key=lambda x:(x[0], x[1].y0))
                x_values += [(rect.x0, rect.x1) for _, rect in locs]

            if alignment is Alignment.RIGHT:
                x_values = sorted(x_values, key=lambda x: x[1], 
                    reverse=True)
                if len(x_values) >0:
                    x_limit = x_values[:int(len(items) * 1.1)][-1][1]
                else:
                    x_limit = 0
                
                def check(rect):
                    return rect.x1 > x_limit
            elif alignment is Alignment.LEFT:
                x_values = sorted(x_values, key=lambda x: x[0], 
                    reverse=False)
                if len(x_values) >0:
                    x_limit = x_values[:int(len(items) * 1.1)][-1][0]
                else:
                    x_limit = 0
                
                def check(rect):
                    return rect.x1 < x_limit
            else:
                def check(rect):
                    return False
            
                    
            for idf, locs in items.items():
                items_source[idf] = 0

                for i, (page, rect) in enumerate(locs):
                    if check(rect):
                        items_source[idf] = i
                        break

    def create_links(self):
        n_link = [0] * len(self.patterns)
        doc = fitz.open(self.file)

        for i_pattern, (items, items_source) in enumerate(zip(self.items, self.items_source)):
            for idf, locs in items.items():
                source_i = items_source[idf]
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
    
    # def save(self, output):
    #     self.doc.save(output)
