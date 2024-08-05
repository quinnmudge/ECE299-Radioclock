from machine import Pin, SPI, I2C, RTC, Timer, PWM
from buzzer_music import music
from time import sleep
import ssd1306
import utime
import rda5807
EncoderA = machine.Pin(27, machine.Pin.IN, machine.Pin.PULL_UP)
EncoderB = machine.Pin(28, machine.Pin.IN, machine.Pin.PULL_UP)
machine.Pin(23, machine.Pin.OUT)
# Initialize variables to keep track of encoder state
A_state = 0
B_state = 0
A_rising_edge = False
A_falling_edge = False
B_rising_edge = False
B_falling_edge = False
rotation_direction = 0  # 1 for clockwise, -1 for counterclockwise

current_posx = 1
current_posy = 4
# Interrupt handler for EncoderA pin

grid_size_x = 42
grid_size_y = 10
ENTER = False


# Define button pins
button_1 = Pin(13, Pin.IN, Pin.PULL_DOWN)  # Button for moving left
enter = Pin(5, Pin.IN, Pin.PULL_DOWN)     # Button for enter

# Debouncing variables
last_pressed_time = 0
debounce_delay = 50  # Adjusted for non-blocking debounce
radio_programming_timer = utime.ticks_ms()
# RTC Setup
rtc = RTC()
rtc.datetime((2024, 7, 10, 0, 0, 0, 0, 0))  # Set initial RTC time (year, month, day, weekday, hours, minutes, seconds, subseconds)
SNOOZE = [0,0,0,0,0,0,0,0]

def floats_are_equal(a: float, b: float, tolerance: float = 0.05) -> bool:
    return abs(a - b) <= tolerance

class Icon:
    def __init__(self, txt, pos_x, pos_y, border):
        #text displayed by the icon
        self.text = txt
        #position of the icon on the screen
        self.xpos_text = pos_x * grid_size_x + 2
        self.ypos_text = pos_y * grid_size_y + 2
        #width and height of the icon's border
        self.width = grid_size_x + 2
        self.height = grid_size_y + 2
        #decide whether to show border (white rectangle) or not
        self.has_border = border
        
class Button(Icon):
    def __init__(self, txt, pos_x, pos_y, select, has_border):
        super().__init__(txt, pos_x, pos_y, has_border)
        self.grid_x = pos_x
        self.grid_y = pos_y
        #used to track if the selector's position matches the button's position
        self.selected = select
        #track what state change should occur when button is pressed
        self.state = None  # Initially no state assigned
    #setter function to set the "state" member
    def configureState(self, the_state):
        self.state = the_state

class Display:
    def __init__(self, width, height):
        self.spi_sck = Pin(18)
        self.spi_sda = Pin(19)
        self.spi_res = Pin(16)
        self.spi_dc = Pin(17)
        self.spi_cs = Pin(20)
        SPI_DEVICE = 0
        self.oled_spi = SPI(SPI_DEVICE, baudrate=100000, sck=self.spi_sck, mosi=self.spi_sda)
        self.SSD = ssd1306.SSD1306_SPI(width, height, self.oled_spi, self.spi_dc, self.spi_res, self.spi_cs)
        self.SSD.fill(0)
        self.SSD.show()

    def invert_region(self, x, y, width, height):
        # Invert a specific region on the display
        for i in range(x, x + width):
            for j in range(y, y + height):
                pixel = self.SSD.pixel(i, j)
                self.SSD.pixel(i, j, not pixel)

    def update_buttons(self, icons):
        global current_state, ENTER, current_posx, current_posy
        #loop over the list of icons being rendered
        for icon in icons:
            #only buttons have functionality and must be updated
            if isinstance(icon, Button):
                #if the button position matches the selector position set "selected" 
                #boolean True
                if icon.grid_x == current_posx and icon.grid_y == current_posy:
                    icon.selected = True
                   # if the encoder button has been pressed and the 
                    # selected button has a state assigned, change states
                    if ENTER and icon.state:
                        current_state = icon.state
                        #current_state.update()
                        change_state(current_state)
                    #reset enter variable (to wait for next encoder button press)
                    ENTER = False
                else:
                    icon.selected = False

    def render(self, icons):
        global current_state
        self.SSD.fill(0)
        for icon in icons:
            if isinstance(icon, Button) and icon.selected:
                # Draw the icon text first
            
                self.SSD.text(icon.text, icon.xpos_text, icon.ypos_text, 1)
                # Invert the region of the selected icon
                if(len(icon.text)==6):
                    self.invert_region(icon.xpos_text - 2, icon.ypos_text - 2, icon.width+5, icon.height)
                else:
                    self.invert_region(icon.xpos_text - 2, icon.ypos_text - 2, icon.width, icon.height)
               
            else:
                self.SSD.text(icon.text, icon.xpos_text, icon.ypos_text, 1)  # Normal text color
                if icon.has_border:
                    self.SSD.rect(icon.xpos_text - 2, icon.ypos_text - 2, icon.width, icon.height, 1)  # Normal border
        self.SSD.show()
        
class State:
    def __init__(self):
        global display
        self.display = display
    def B1Handler(pin):
        pass
    def ENCA(self, pin):
        pass 
    # Interrupt handler for EncoderB pin (optional, if needed)
    def ENCB(self, pin):
        pass
    def convert_to_12h(self,hour, minute):
        if hour >= 0 and hour < 12:
            period = "AM"
            if hour == 0:
                hour = 12  # 0 AM is 12 AM in 12-hour format
        else:
            period = "PM"
            if hour > 12:
                hour -= 12  # Convert PM hours to 12-hour format
        
        return f"{hour}:{minute:02d} {period}"

def update(self):
    pass


