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

class RadioState(State):
    def __init__(self):
        super().__init__()
        global radio, Menu_s
        #_, _, frequency, _ = radio.GetSettings()
        self.freq = 101.9
        self.volume = 1
        self.is_on = "N"
        self.stationName = "CFUV"
        self.radioOn = Button("On: " + self.is_on,1,0,False,True)
        self.station = Icon(str(self.stationName),1,4,False)
        self.frequency_text = Icon("Freq:",0,3,False)
        self.volume_text = Icon("Volume:",0,2,False)
        self.seek = Button("Seek",0,0,False,True)
        self.frequ_disp = Button("  "+str(self.freq)+"FM", 1, 3,False, False)
        self.menu = Button("Menu",0,5,True,True)
        self.menu.configureState(Menu_s)
        self.vol_adj = Button("Vol.",1,5,False,True)
        self.vol_disp = Icon(str(self.volume),2,2,False)
        self.freq_adj = Button("Freq.",2,5,False,True)
        self.icons = [self.frequ_disp, self.menu, self.vol_adj, self.freq_adj,self.vol_disp,self.frequency_text, self.volume_text,self.radioOn, self.seek, self.station]
        self.start_posx = 0
        self.start_posy = 5
   
    def update(self):
        self.menu.configureState(Menu_s)
        display.update_buttons(self.icons)
    
    def setStationName(self):
        if (floats_are_equal(self.freq , 101.9)):
            self.station.text = "CFUV"
        elif(floats_are_equal(self.freq , 88.9)):
            self.station.text = "CBUX"
        elif(floats_are_equal(self.freq , 90.5)):
            self.station.text = "CBCV"
        elif(floats_are_equal(self.freq , 91.3)):
            self.station.text = "CJZN"
        elif(floats_are_equal(self.freq , 92.1)):
            self.station.text = "CBU"
        elif(floats_are_equal(self.freq , 98.5)):
            self.station.text = "CIOC"
        elif(floats_are_equal(self.freq , 99.7)):
            self.station.text = "CBUF"
        elif(floats_are_equal(self.freq , 100.3)):
            self.station.text = "CKKQ"
        elif(floats_are_equal(self.freq , 103.1)):
            self.station.text = "CHTT"
        elif(floats_are_equal(self.freq , 106.5)):
            self.station.text = "KWPZ"
        elif(floats_are_equal(self.freq , 107.3)):
            self.station.text = "CHBE"
        elif(floats_are_equal(self.freq , 107.9)):
            self.station.text = "CILS"
        elif(floats_are_equal(self.freq , 104.1)):
            self.station.text = "KAFE"
        else:
            self.station.text = ""
                
    
    def ENCA(self,pin):
        global A_state, A_rising_edge, A_falling_edge, rotation_direction, radio
       
        # Read current state of EncoderA and EncoderB pins
        A_state = EncoderA.value()
        B_state = EncoderB.value()
        
        # Determine edge detection on EncoderA
        if A_state == 1 and B_state == 0:
            A_rising_edge = True
        elif A_state == 0 and B_state == 1:
            A_falling_edge = True
        
        # Check for both rising and falling edges on EncoderA
        if A_rising_edge and A_falling_edge:
            if A_state != B_state:
                #adjust volume
                if(self.vol_adj.selected):
                    if(self.volume+1 <=5): 
                        radio.set_volume(self.volume+1 ) 
                        radio.update_rds()
                        self.volume+=1
                        self.vol_disp.text = str(self.volume)
                #turn radio on and off        
                if(self.radioOn.selected):
                    if(self.is_on == "N"):
                        self.is_on = "Y"
                        self.radioOn.text = "On: " + self.is_on
                        radio.mute(False)
                        radio.update_rds()
                    else:
                        self.is_on = "N"
                        self.radioOn.text = "On: " + self.is_on
                        radio.mute(True)
                        radio.update_rds()
                 #adjust frequency       
                 if(self.freq_adj.selected):
         
                   if(self.freq+0.1 <= 108):
                       radio.set_frequency_MHz(self.freq +0.1)
                       self.freq +=0.1
                       radio.update_rds()
                       # Update the frequency displayed on the icon
                       self.frequ_disp.text = "  "+f"{self.freq:.1f}"+"FM"
                       self.setStationName()
                #seek up        
                if(self.seek.selected):
                    radio.seek_up()
                    self.freq = radio.get_frequency_MHz()
                    self.frequ_disp.text = "  "+f"{self.freq:.1f}"+"FM"
                    self.setStationName() 
                #render updated information to display    
                display.render(self.icons)
            else:
               pass
            
            # Reset edge detection flags
            A_rising_edge = False
            A_falling_edge = False
            
    # Interrupt handler for EncoderB pin (optional, if needed)
    def ENCB(self,pin):
        global B_state, B_rising_edge, B_falling_edge, rotation_direction, radio
        # Read current state of EncoderA and EncoderB pins
        A_state = EncoderA.value()
        B_state = EncoderB.value()
        
        # Determine edge detection on EncoderB
        if B_state == 1 and A_state == 0:
            B_rising_edge = True
        elif B_state == 0 and A_state == 1:
            B_falling_edge = True
        
        # Check for both rising and falling edges on EncoderB
        if B_rising_edge and B_falling_edge:
            if A_state == B_state:
                pass
                
            else:
                if(self.freq_adj.selected):
                    if(self.freq-0.1 >= 88):
                        radio.set_frequency_MHz(self.freq-0.1)
                        self.freq-=0.1
                        radio.update_rds()
                        # Update the frequency displayed on the icon
                        self.frequ_disp.text = "  "+f"{self.freq:.1f}"+"FM"
                        self.setStationName()                  

                if(self.vol_adj.selected):
                    if(self.volume-1 >=0):
                        radio.set_volume( self.volume-1 )
                        radio.update_rds()
                        self.volume-=1
                        self.vol_disp.text = str(self.volume)
                if(self.radioOn.selected):
                    if(self.is_on == "N"):
                        self.is_on = "Y"
                        self.radioOn.text = "On: " + self.is_on
                        radio.mute(False)
                        radio.update_rds() 
                    else:
                        self.is_on = "N"
                        self.radioOn.text = "On: " + self.is_on
                        radio.mute(True)
                        radio.update_rds()
                if(self.seek.selected):
                    radio.seek_down()
                    self.freq = radio.get_frequency_MHz()
                    self.frequ_disp.text = "  "+f"{self.freq:.1f}"+"FM"
                    self.setStationName()                    

                display.render(self.icons)
                
            # Reset edge detection flags
            B_rising_edge = False
            B_falling_edge = False
 
    def B1Handler(self,pin):
        global current_posx, current_posy
        if debounce_handler(pin):
            current_posx -=1
            if(current_posx<0 and current_posy != 0):
                current_posx = 1
                current_posy = 0
            if(current_posx==-1 and current_posy ==0):
                current_posx = 2
                current_posy = 5
            
            self.update()
            display.render(self.icons)
           
    def B2Handler(self,pin):
        pass
            
           
            
class MainMenuState(State):
    def __init__(self):
        super().__init__()
        global icons
        self.clock_but = Button("CLOCK", 1, 0, False, True)
        self.radio_but = Button("RADIO", 1, 2, False, True)
        self.alarm_but = Button("ALARM", 1, 4, True, True)
        self.clock_but.configureState(Clock_s)
        self.radio_but.configureState(Radio_s)
        self.alarm_but.configureState(Alarm_s)
        self.icons = [self.radio_but, self.alarm_but, self.clock_but]
        self.start_posx = 1
        self.start_posy = 4
        display.render(self.icons)
    def update(self):
        display.update_buttons(self.icons)
    def B1Handler(self,pin):
         global current_state, current_posy
         if debounce_handler(pin):
            current_posy -= 2
            if(current_posy<0):
                current_posy = 4
            self.update()
            display.render(self.icons)
    
    def ENCA(self,pin):
        pass
            
    # Interrupt handler for EncoderB pin (optional, if needed)
    def ENCB(self,pin):
        pass

def debounce_handler(pin):
    global last_pressed_time
    current_time = utime.ticks_ms()
    if current_time - last_pressed_time < debounce_delay:
        return False
    last_pressed_time = current_time
    return pin.value() == 0  # Check if button is pressed

#interrupt handler for the encoder button
def Enter_Handler(pin):
    global ENTER, current_state
    if debounce_handler(pin):
        ENTER = True
        
def change_state(state):
    global current_state, current_posx, current_posy
    current_state = state
    current_posx = current_state.start_posx
    current_posy = current_state.start_posy
    EncoderA.irq(trigger=machine.Pin.IRQ_RISING | machine.Pin.IRQ_FALLING, handler=current_state.ENCA)
    EncoderB.irq(trigger=machine.Pin.IRQ_RISING | machine.Pin.IRQ_FALLING, handler=current_state.ENCB)
    button_1.irq(handler=current_state.B1Handler, trigger=Pin.IRQ_FALLING)
    current_state.update()
    display.render(current_state.icons)
    
class ClockRadio:
    def __init__(self):
        global Radio_s, current_state
        button_1.irq(handler=current_state.B1Handler, trigger=Pin.IRQ_FALLING)
        EncoderA.irq(trigger=machine.Pin.IRQ_RISING | machine.Pin.IRQ_FALLING, handler=current_state.ENCA)
        EncoderB.irq(trigger=machine.Pin.IRQ_RISING | machine.Pin.IRQ_FALLING, handler=current_state.ENCB)
        enter.irq(handler=Enter_Handler, trigger=Pin.IRQ_FALLING)

    def update(self, state):
        global radio_programming_timer
        state.update()
        pass
           
display = Display(128,64)
radio_i2c = I2C(0, sda=Pin(0), scl = Pin(1), freq=100000) # What frequency should we use?
radio = rda5807.Radio(radio_i2c)
utime.sleep(1)
radio.set_frequency_MHz(101.9)
radio.set_volume(3)
radio.mute(True)
radio.update_rds()    
Menu_s = None
Radio_s = RadioState()
Menu_s = MainMenuState()
#define states used by the clock radio before the clock radio
current_state = Menu_s
clock_radio = ClockRadio()

while True:
    clock_radio.update(current_state)
