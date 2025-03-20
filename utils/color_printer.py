from colorama import Fore, Back, Style, init

init(autoreset=True)

class ColorPrinter:
    BLACK = Fore.BLACK
    RED = Fore.RED
    GREEN = Fore.GREEN
    YELLOW = Fore.YELLOW
    BLUE = Fore.BLUE
    MAGENTA = Fore.MAGENTA
    CYAN = Fore.CYAN
    WHITE = Fore.WHITE
    LIGHTBLACK_EX = Fore.LIGHTBLACK_EX
    LIGHTRED_EX = Fore.LIGHTRED_EX
    LIGHTGREEN_EX = Fore.LIGHTGREEN_EX
    LIGHTYELLOW_EX = Fore.LIGHTYELLOW_EX
    LIGHTBLUE_EX = Fore.LIGHTBLUE_EX
    LIGHTMAGENTA_EX = Fore.LIGHTMAGENTA_EX
    LIGHTCYAN_EX = Fore.LIGHTCYAN_EX
    LIGHTWHITE_EX = Fore.LIGHTWHITE_EX

    BG_BLACK = Back.BLACK
    BG_RED = Back.RED
    BG_GREEN = Back.GREEN
    BG_YELLOW = Back.YELLOW
    BG_BLUE = Back.BLUE
    BG_MAGENTA = Back.MAGENTA
    BG_CYAN = Back.CYAN
    BG_WHITE = Back.WHITE
    BG_LIGHTBLACK_EX = Back.LIGHTBLACK_EX
    BG_LIGHTRED_EX = Back.LIGHTRED_EX
    BG_LIGHTGREEN_EX = Back.LIGHTGREEN_EX
    BG_LIGHTYELLOW_EX = Back.LIGHTYELLOW_EX
    BG_LIGHTBLUE_EX = Back.LIGHTBLUE_EX
    BG_LIGHTMAGENTA_EX = Back.LIGHTMAGENTA_EX
    BG_LIGHTCYAN_EX = Back.LIGHTCYAN_EX
    BG_LIGHTWHITE_EX = Back.LIGHTWHITE_EX

    RESET = Style.RESET_ALL
    BRIGHT = Style.BRIGHT
    DIM = Style.DIM
    NORMAL = Style.NORMAL

    ERROR = Fore.RED + Style.BRIGHT
    WARNING = Fore.YELLOW
    SUCCESS = Fore.GREEN + Style.BRIGHT
    INFO = Fore.BLUE

    def black(self, text):
        return f"{self.BLACK}{text}{self.RESET}"

    def red(self, text):
        return f"{self.RED}{text}{self.RESET}"

    def green(self, text):
        return f"{self.GREEN}{text}{self.RESET}"

    def yellow(self, text):
        return f"{self.YELLOW}{text}{self.RESET}"

    def blue(self, text):
        return f"{self.BLUE}{text}{self.RESET}"

    def magenta(self, text):
        return f"{self.MAGENTA}{text}{self.RESET}"

    def cyan(self, text):
        return f"{self.CYAN}{text}{self.RESET}"

    def white(self, text):
        return f"{self.WHITE}{text}{self.RESET}"

    def lightblack_ex(self, text):
        return f"{self.LIGHTBLACK_EX}{text}{self.RESET}"

    def lightred_ex(self, text):
        return f"{self.LIGHTRED_EX}{text}{self.RESET}"

    def lightgreen_ex(self, text):
        return f"{self.LIGHTGREEN_EX}{text}{self.RESET}"

    def lightyellow_ex(self, text):
        return f"{self.LIGHTYELLOW_EX}{text}{self.RESET}"

    def lightblue_ex(self, text):
        return f"{self.LIGHTBLUE_EX}{text}{self.RESET}"

    def lightmagenta_ex(self, text):
        return f"{self.LIGHTMAGENTA_EX}{text}{self.RESET}"

    def lightcyan_ex(self, text):
        return f"{self.LIGHTCYAN_EX}{text}{self.RESET}"

    def lightwhite_ex(self, text):
        return f"{self.LIGHTWHITE_EX}{text}{self.RESET}"

    def bg_black(self, text):
        return f"{self.BG_BLACK}{text}{self.RESET}"

    def bg_red(self, text):
        return f"{self.BG_RED}{text}{self.RESET}"

    def bg_green(self, text):
        return f"{self.BG_GREEN}{text}{self.RESET}"

    def bg_yellow(self, text):
        return f"{self.BG_YELLOW}{text}{self.RESET}"

    def bg_blue(self, text):
        return f"{self.BG_BLUE}{text}{self.RESET}"

    def bg_magenta(self, text):
        return f"{self.BG_MAGENTA}{text}{self.RESET}"

    def bg_cyan(self, text):
        return f"{self.BG_CYAN}{text}{self.RESET}"

    def bg_white(self, text):
        return f"{self.BG_WHITE}{text}{self.RESET}"

    def bg_lightblack_ex(self, text):
        return f"{self.BG_LIGHTBLACK_EX}{text}{self.RESET}"

    def bg_lightred_ex(self, text):
        return f"{self.BG_LIGHTRED_EX}{text}{self.RESET}"

    def bg_lightgreen_ex(self, text):
        return f"{self.BG_LIGHTGREEN_EX}{text}{self.RESET}"

    def bg_lightyellow_ex(self, text):
        return f"{self.BG_LIGHTYELLOW_EX}{text}{self.RESET}"

    def bg_lightblue_ex(self, text):
        return f"{self.BG_LIGHTBLUE_EX}{text}{self.RESET}"

    def bg_lightmagenta_ex(self, text):
        return f"{self.BG_LIGHTMAGENTA_EX}{text}{self.RESET}"

    def bg_lightcyan_ex(self, text):
        return f"{self.BG_LIGHTCYAN_EX}{text}{self.RESET}"

    def bg_lightwhite_ex(self, text):
        return f"{self.BG_LIGHTWHITE_EX}{text}{self.RESET}"

    def bright_black(self, text):
        return f"{self.BRIGHT}{self.BLACK}{text}{self.RESET}"

    def bright_red(self, text):
        return f"{self.BRIGHT}{self.RED}{text}{self.RESET}"

    def bright_green(self, text):
        return f"{self.BRIGHT}{self.GREEN}{text}{self.RESET}"

    def bright_yellow(self, text):
        return f"{self.BRIGHT}{self.YELLOW}{text}{self.RESET}"

    def bright_blue(self, text):
        return f"{self.BRIGHT}{self.BLUE}{text}{self.RESET}"

    def bright_magenta(self, text):
        return f"{self.BRIGHT}{self.MAGENTA}{text}{self.RESET}"

    def bright_cyan(self, text):
        return f"{self.BRIGHT}{self.CYAN}{text}{self.RESET}"

    def bright_white(self, text):
        return f"{self.BRIGHT}{self.WHITE}{text}{self.RESET}"

    def bright_lightblack_ex(self, text):
        return f"{self.BRIGHT}{self.LIGHTBLACK_EX}{text}{self.RESET}"

    def bright_lightred_ex(self, text):
        return f"{self.BRIGHT}{self.LIGHTRED_EX}{text}{self.RESET}"

    def bright_lightgreen_ex(self, text):
        return f"{self.BRIGHT}{self.LIGHTGREEN_EX}{text}{self.RESET}"

    def bright_lightyellow_ex(self, text):
        return f"{self.BRIGHT}{self.LIGHTYELLOW_EX}{text}{self.RESET}"

    def bright_lightblue_ex(self, text):
        return f"{self.BRIGHT}{self.LIGHTBLUE_EX}{text}{self.RESET}"

    def bright_lightmagenta_ex(self, text):
        return f"{self.BRIGHT}{self.LIGHTMAGENTA_EX}{text}{self.RESET}"

    def bright_lightcyan_ex(self, text):
        return f"{self.BRIGHT}{self.LIGHTCYAN_EX}{text}{self.RESET}"

    def bright_lightwhite_ex(self, text):
        return f"{self.BRIGHT}{self.LIGHTWHITE_EX}{text}{self.RESET}"

    def error(self, text):
        return f"{self.ERROR}{text}{self.RESET}"

    def warning(self, text):
        return f"{self.WARNING}{text}{self.RESET}"

    def success(self, text):
        return f"{self.SUCCESS}{text}{self.RESET}"

    def info(self, text):
        return f"{self.INFO}{text}{self.RESET}"


cpr = ColorPrinter()