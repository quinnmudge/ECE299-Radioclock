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
class ClockState(State):
    def __init__(self):
        global Alarm_s
        super().__init__()  # Initialize superclass Display
        self.menu = Button("Menu",0,5,True,True)
        self.menu.configureState(Menu_s)
        self.format_time = "12h"
        self.Alarm_on = Icon("Al: " +Alarm_s.is_on,2,0,False)
        self.hour_adj = Button("Hr.",1,5,False,True)
        self.min_adj = Button("Min",2,5,False,True)
        self.format_adj = Button(self.format_time,0,0,False,True)
        self.zone = -7
        self.zone_text = "UTC"+str(self.zone)
        self.time_zone = Button(self.zone_text,1,0,False,True)
        self.start_posx = 0
        self.start_posy = 5
        self.clock = Icon("", 1, 3, False)  # Placeholder for the clock icon
        self.update_time()  # Initialize the clock display
        self.icons = [self.clock, self.menu, self.hour_adj, self.min_adj,self.format_adj,self.time_zone,self.Alarm_on]
        # Timer setup for minute update
        self.timer = Timer()
        self.timer.init(period=60000, mode=Timer.PERIODIC, callback=self.timer_callback)
        

    def update_time(self):
        year, month, day, weekday, hours, minutes, seconds, subseconds = rtc.datetime()
        
        if(self.format_time=="24h"):
            clock_text = '{:02d}:{:02d}'.format(hours, minutes)
        else:
            clock_text = self.convert_to_12h(hours,minutes)

        self.clock.text = clock_text
    def update(self):
        self.menu.configureState(Menu_s)
        self.Alarm_on.text = " Al:" +Alarm_s.is_on
        display.update_buttons(self.icons)
    def timer_callback(self, timer):
        global current_state
        self.update_time()
        if(isinstance(current_state,ClockState)):
            display.render(self.icons)
        else:
            pass
       

    def B1Handler(self,pin):
         global current_state, current_posx, current_posy
         if debounce_handler(pin):
            if(current_posx <= 0 and current_posy ==5):
                current_posy=0
                current_posx = 1
            elif(current_posx<=0 and current_posy ==0):
                current_posy=5
                current_posx=2
            else:
                current_posx -= 1
            self.update()
            display.render(self.icons)
            
    def ENCA(self, pin):
        global A_state, A_rising_edge, A_falling_edge, rotation_direction, radio, rtc,SNOOZE
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
            year, month, day, weekday, hours, minutes, seconds, subseconds = rtc.datetime()
            if A_state != B_state:
                if self.hour_adj.selected:
                    if hours+1<=23:
                        rtc.datetime((year, month, day, weekday, (hours+1), minutes, seconds, subseconds))
                        if(minutes + Alarm_s.snoozeLength >= 60):
                           hours+=1
                           minutes = (minutes + Alarm_s.snoozeLength) % 60
                           SNOOZE = [year, month, day, weekday, hours+1, minutes, seconds, subseconds]
                        else:
                           SNOOZE = [year, month, day, weekday, hours+1, minutes+Alarm_s.snoozeLength, seconds, subseconds]
                    else:
                        pass
                if self.min_adj.selected:
                    if minutes+1<=59:
                        rtc.datetime((year, month, day, weekday, hours, (minutes+1), seconds, subseconds))
                        if(minutes + Alarm_s.snoozeLength >= 60):
                           hours+=1
                           minutes = (minutes + Alarm_s.snoozeLength) % 60
                           SNOOZE = [year, month, day, weekday, hours, minutes+1, seconds, subseconds]
                        else:
                           SNOOZE = [year, month, day, weekday, hours, minutes+Alarm_s.snoozeLength+1, seconds, subseconds]
                    else:
                        pass
                if self.format_adj.selected:
                  
                    if(self.format_time =="24h"):
                        self.format_time = "12h"
                    else:
                        self.format_time = "24h"
                    self.format_adj.text = self.format_time
                if self.time_zone.selected:
                    if(self.zone<14):
                        if(hours+1 > 23):
                            day+=1
                            weekday+=1
                            hours = -1
                        self.zone+=1
                        rtc.datetime((year, month, day, weekday, (hours+1), minutes, seconds, subseconds))
                        if(minutes + Alarm_s.snoozeLength >= 60):
                           hours+=1
                           minutes = (minutes + Alarm_s.snoozeLength) % 60
                           SNOOZE = [year, month, day, weekday, hours+1, minutes, seconds, subseconds]
                        else:
                           SNOOZE = [year, month, day, weekday, hours+1, minutes+Alarm_s.snoozeLength, seconds, subseconds]
                        self.time_zone.text = "UTC"+str(self.zone)
            else:
                pass
            
            # Reset edge detection flags
            A_rising_edge = False
            A_falling_edge = False
            self.update_time()
            display.render(self.icons)

    # Interrupt handler for EncoderB pin (optional, if needed)
    def ENCB(self, pin):
        global B_state, B_rising_edge, B_falling_edge, rotation_direction, radio, SNOOZE
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
            year, month, day, weekday, hours, minutes, seconds, subseconds = rtc.datetime()
            if A_state == B_state:
                pass
            else:
                if self.hour_adj.selected:
                    if hours-1>=0 :
                        rtc.datetime((year, month, day, weekday, (hours-1), minutes, seconds, subseconds))
                        if(minutes + Alarm_s.snoozeLength >= 60):
                           hours+=1
                           minutes = (minutes + Alarm_s.snoozeLength) % 60
                           SNOOZE = [year, month, day, weekday, hours-1, minutes, seconds, subseconds]
                        else:
                           SNOOZE = [year, month, day, weekday, hours-1, minutes+Alarm_s.snoozeLength, seconds, subseconds]
                            
                    else:
                        pass
                   
                if self.min_adj.selected:
                    year, month, day, weekday, hours, minutes, seconds, subseconds = rtc.datetime()
                    if minutes -1>=0:
                        rtc.datetime((year, month, day, weekday, hours, (minutes-1), seconds, subseconds))
                        if(minutes + Alarm_s.snoozeLength >= 60):
                           hours+=1
                           minutes = (minutes + Alarm_s.snoozeLength) % 60
                           SNOOZE = [year, month, day, weekday, hours, minutes-1, seconds, subseconds]
                        else:
                           SNOOZE = [year, month, day, weekday, hours, minutes+Alarm_s.snoozeLength-1, seconds, subseconds]
                    else:
                        pass
                if self.format_adj.selected:
                   
                    if(self.format_time =="24h"):
                        self.format_time = "12h"
                    else:
                        self.format_time = "24h"
                        
                    self.format_adj.text = self.format_time
                if self.time_zone.selected:
                    if(self.zone>-11):
                        if(hours-1 < 0):
                            hours=24
                            weekday-=1
                            day-=1
                        self.zone-=1
                        
                        rtc.datetime((year, month, day, weekday, (hours-1), minutes, seconds, subseconds))
                        if(minutes + Alarm_s.snoozeLength >= 60):
                           hours+=1
                           minutes = (minutes + Alarm_s.snoozeLength) % 60
                           SNOOZE = [year, month, day, weekday, hours-1, minutes, seconds, subseconds]
                        else:
                           SNOOZE = [year, month, day, weekday, hours-1, minutes+Alarm_s.snoozeLength, seconds, subseconds]
                        self.time_zone.text = "UTC"+str(self.zone)
                      
                
                # Reset edge detection flags
            B_rising_edge = False
            B_falling_edge = False
            self.update_time()
            display.render(self.icons)

