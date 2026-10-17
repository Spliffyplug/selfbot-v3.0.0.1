import re

class AsciiHelper:

    @staticmethod
    def _block(lines):
        body = '\n'.join((str(x) for x in lines))
        if len(body) > 1900:
            body = body[:1897] + '...'
        return '```ansi\n' + body + '\n```'

    @staticmethod
    def _clean_empty_lines(content: str) -> str:
        lines = content.split('\n')
        return '\n'.join((l for l in lines if not re.match('^>\\s*$', l)))

    @staticmethod
    def format(message, username=None):
        return AsciiHelper._block([f'\x1b[2;37m{message}\x1b[0m'])

    @staticmethod
    def multiline(lines, raw=False):
        if raw:
            return AsciiHelper._block(list(lines))
        return AsciiHelper._block([f'\x1b[2;37m{l}\x1b[0m' for l in lines])

    @staticmethod
    def info(message):
        return AsciiHelper._block([f'\x1b[36m|\x1b[0m  \x1b[2;37m{message}\x1b[0m'])

    @staticmethod
    def success(message):
        return AsciiHelper._block([f'\x1b[32mok\x1b[0m  \x1b[2;37m{message}\x1b[0m'])

    @staticmethod
    def error(message):
        return AsciiHelper._block([f'\x1b[31merr\x1b[0m  \x1b[2;37m{message}\x1b[0m'])

    @staticmethod
    def warning(message):
        return AsciiHelper._block([f'\x1b[33m!\x1b[0m  \x1b[2;37m{message}\x1b[0m'])

    @staticmethod
    def custom(message, color='37'):
        return AsciiHelper._block([f'\x1b[2;{color}m{message}\x1b[0m'])

    @staticmethod
    def table(rows):
        return AsciiHelper._block([f'\x1b[2;37m{r}\x1b[0m' for r in rows])
