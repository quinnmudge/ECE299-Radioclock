from machine import Pin, SPI
import ssd1306
import utime

grid_size_x = 42
grid_size_y = 10

class Icon:
    def __init__(self, txt, pos_x, pos_y, has_border):
        global grid_size_x, grid_size_y
        self.text = txt
        self.xpos_text = pos_x * grid_size_x
        self.ypos_text = pos_y * grid_size_y
        self.width = grid_size_x + 2
        self.height = grid_size_y + 2
        self.border = has_border

class Button(Icon):
    def __init__(self, txt, pos_x, pos_y, has_border):
        super().__init__(txt, pos_x, pos_y, has_border)

class Display:
    def __init__(self, width, height):
        self.init_buttons()
        self.spi_sck = Pin(18)
        self.spi_sda = Pin(19)
        self.spi_res = Pin(16)
        self.spi_dc  = Pin(17)
        self.spi_cs  = Pin(20)
        SPI_DEVICE = 0  # Define your SPI device constant
        self.oled_spi = SPI(SPI_DEVICE, baudrate=100000, sck=self.spi_sck, mosi=self.spi_sda)
        self.SSD = ssd1306.SSD1306_SPI(width, height, self.oled_spi, self.spi_dc, self.spi_res, self.spi_cs)
        self.SSD.fill(0)
        self.SSD.show()

    def init_buttons(self):
        # Initialize buttons here if needed
        pass

    def update(self, icons):
        self.SSD.fill(0)
        for icon in icons:
            self.SSD.text(icon.text, icon.xpos_text, icon.ypos_text)
            if icon.border:
                self.SSD.rect(icon.xpos_text - 1, icon.ypos_text - 1, icon.width, icon.height, 1)
        self.SSD.show()

class State:
    pass

class ClockState(State):
    def __init__(self, h, m):
        self.hour = h
        self.minute = m
        self.radio = Button("RADIO", 0, 0, True)
        self.alarm = Button("ALARM",1,0,True)
        self.menu = [self.radio, self.alarm]
        self.display = Display(128, 64)

    def update(self):
        self.display.update(self.menu)
        self.display.SSD.show()

class ClockRadio:
    def __init__(self):
        self.current_state = ClockState(12, 0)

    def run(self):
        self.update(self.current_state)

    def update(self, state):
        if isinstance(state, ClockState):
            state.update()
        # Add handling for other states if needed
        # if isinstance(state, RadioState):
        #     state.update()

clock_radio = ClockRadio()

while True:
    clock_radio.run()
    utime.sleep(1)  # Add a delay to prevent overwhelming the CPU

