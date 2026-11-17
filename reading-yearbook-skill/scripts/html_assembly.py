"""Insert packaged fragments at real HTML end tags, never JavaScript literals."""
from html.parser import HTMLParser


def insert_before_closing_tag(page, tag, fragment):
    # HTMLParser counts only LF as a new line, unlike str.splitlines().
    offsets = [0] + [index + 1 for index, char in enumerate(page) if char == '\n']
    class Positions(HTMLParser):
        position = None
        def handle_endtag(self, name):
            if name == tag.lower():
                row, column = self.getpos()
                self.position = offsets[row - 1] + column
    parser = Positions(convert_charrefs=False)
    parser.feed(page)
    if parser.position is None:
        raise ValueError('HTML缺少结束标签：' + tag)
    position = parser.position
    return page[:position] + fragment + page[position:]
