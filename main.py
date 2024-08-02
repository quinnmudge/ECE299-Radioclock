
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
button_2 = Pin(12, Pin.IN, Pin.PULL_DOWN)  # Button for moving right
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
        self.text = txt
        self.xpos_text = pos_x * grid_size_x + 2
        self.ypos_text = pos_y * grid_size_y + 2
        self.width = grid_size_x + 2
        self.height = grid_size_y + 2
        self.has_border = border

class Button(Icon):
    def __init__(self, txt, pos_x, pos_y, select, has_border):
        super().__init__(txt, pos_x, pos_y, has_border)
        self.grid_x = pos_x
        self.grid_y = pos_y
        self.selected = select
        self.state = None  # Initially no state assigned

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
        
        for icon in icons:
            if isinstance(icon, Button):
                if icon.grid_x == current_posx and icon.grid_y == current_posy:
                    icon.selected = True
                 
                    if ENTER and icon.state:
                        current_state = icon.state
                        #current_state.update()
                        change_state(current_state)
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
                if(self.freq_adj.selected):
                 #  radio.seek_up() #THIS GOES TO THE NEXT CHANNEL
                   if(self.freq+0.1 <= 108):
                       radio.set_frequency_MHz(self.freq +0.1)
                       self.freq +=0.1
                       radio.update_rds()
                       # Update the frequency displayed on the icon
                       self.frequ_disp.text = "  "+f"{self.freq:.1f}"+"FM"
                       self.setStationName()
                       print(self.freq)
                       print(floats_are_equal(self.freq,100.3))
                if(self.vol_adj.selected):
                    if(self.volume+1 <=5): 
                        radio.set_volume(self.volume+1 ) 
                        radio.update_rds()
                        self.volume+=1
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
                    radio.seek_up()
                    self.freq = radio.get_frequency_MHz()
                    self.frequ_disp.text = "  "+f"{self.freq:.1f}"+"FM"
                    self.setStationName()                    
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
            
      
class AlarmState(State):
    def __init__(self):
        super().__init__()
        global rtc
        self.alarmOn = Button("Alarm",0,4,False,True)
        self.snooze_adj = Button("Sleep",0,3,False,True)
        self.song_adj = Button("Song",0,2,False,True)
        self.volume_adj = Button("Vol:",0,1,False,True)
        self.volume = 3
        self.start_posx = 0
        self.start_posy = 5
        self.snoozeLength = 1
        self.alarm_hour = 0
        self.alarm_minute = 0
        self.song_id = 1
        str_num = '{:02d}'.format(self.alarm_minute)
        self.volume_disp = Icon(" "+str(self.volume),1,1,False)
        self.alarm_disp = Icon(" "+str(self.alarm_hour)+":"+str_num,1,4,False)
        self.snooze_disp = Icon(" "+str(self.snoozeLength) + " Mins",1,3,False)
        self.song_disp = Icon(" " + str(self.song_id),1,2,False)
        self.hour_adj = Button("Hr.",1,5,False,True)
        self.minute_adj = Button("Min.",2,5,False,True)
        self.menu = Button("Menu",0,5,True,True)
        self.menu.configureState(Menu_s)
        self.is_on = "N"
        self.alarm_on = Icon("On: " + self.is_on,2,0,False)
        self.icons = [self.alarm_on,self.volume_disp,self.alarm_disp,self.snooze_disp,self.hour_adj,self.minute_adj,self.menu,self.alarmOn,self.song_adj,self.song_disp,self.snooze_adj, self.volume_adj]
        
    def update(self):
        self.menu.configureState(Menu_s)
        display.update_buttons(self.icons)

    def ENCA(self,pin):
        global A_state, A_rising_edge, A_falling_edge, rotation_direction, radio, mySong
       
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
                if(self.song_adj.selected):
                    if(self.song_id+1 <= 3):
                        self.song_id +=1
                        # Update the frequency displayed on the icon
                        mySong = music(songs[self.song_id-1], pins=[Pin(26)])
                        self.song_disp.text = " " + str(self.song_id)
                if(self.snooze_adj.selected):
                    if (self.snoozeLength+1 < 60 ):
                        self.snoozeLength+=1
                        self.snooze_disp.text = " "+str(self.snoozeLength) + " Mins"
                if self.hour_adj.selected:
                    if self.alarm_hour+1<=23:
                        self.alarm_hour+=1
                        str_num = '{:02d}'.format(self.alarm_minute)
                        if(Clock_s.format_time=="24h"):
                            self.alarm_disp.text = " "+str(self.alarm_hour)+":"+str_num
                        else:
                            self.alarm_disp.text = " "+self.convert_to_12h(self.alarm_hour,self.alarm_minute)
                if self.minute_adj.selected:
                    if self.alarm_minute+1<=59:
                        self.alarm_minute+=1
                        str_num = '{:02d}'.format(self.alarm_minute)
                        if(Clock_s.format_time=="24h"):
                            self.alarm_disp.text = " "+str(self.alarm_hour)+":"+str_num
                        else:
                            self.alarm_disp.text = " "+self.convert_to_12h(self.alarm_hour,self.alarm_minute)
                if(self.alarmOn.selected):
                    if(self.is_on == "N"):
                        self.is_on = "Y"
                        self.alarm_on.text = "On: " + self.is_on
                    else:
                        self.is_on = "N"
                        self.alarm_on.text = "On: " + self.is_on
                if self.volume_adj.selected:
                    if (self.volume + 1) <= 5:
                        self.volume += 1
                        self.volume_disp.text = " "+str(self.volume)
                        mySong.duty = self.volume*2000 + 100
        
                display.render(self.icons)
            else:
                pass
            
            # Reset edge detection flags
            A_rising_edge = False
            A_falling_edge = False        
    # Interrupt handler for EncoderB pin (optional, if needed)
    def ENCB(self,pin):
        global B_state, B_rising_edge, B_falling_edge, rotation_direction, mySong
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
                 #DECREASE LOGIC
                if(self.song_adj.selected):
                    if(self.song_id-1 >= 1):
                        self.song_id -=1
                        self.song_disp.text = " " + str(self.song_id)
                        mySong = music(songs[self.song_id-1], pins=[Pin(26)])
                    # Update the frequency displayed on the icon
                if(self.snooze_adj.selected):
                    if (self.snoozeLength-1 >0 ):
                        self.snoozeLength-=1
                        self.snooze_disp.text = " "+str(self.snoozeLength) + " Mins"
                if self.hour_adj.selected:
                    if self.alarm_hour-1>=0:
                        self.alarm_hour-=1
                        str_num = '{:02d}'.format(self.alarm_minute)
                        if(Clock_s.format_time=="24h"):
                            self.alarm_disp.text = " "+str(self.alarm_hour)+":"+str_num
                        else:
                            self.alarm_disp.text = " "+self.convert_to_12h(self.alarm_hour,self.alarm_minute)
                    else:
                        pass
                if self.minute_adj.selected:
                    if self.alarm_minute-1>=0:
                        self.alarm_minute-=1
                        str_num = '{:02d}'.format(self.alarm_minute)
                        if(Clock_s.format_time=="24h"):
                            self.alarm_disp.text = " "+str(self.alarm_hour)+":"+str_num
                        else:
                            self.alarm_disp.text = " "+self.convert_to_12h(self.alarm_hour,self.alarm_minute)
                    else:
                        pass
                if(self.alarmOn.selected):
                    if(self.is_on == "N"):
                        self.is_on = "Y"
                        self.alarm_on.text = "On: " + self.is_on
                    else:
                        self.is_on = "N"
                        self.alarm_on.text = "On: " + self.is_on
                if(self.volume_adj.selected):
                    if(self.volume - 1 >= 0):
                        self.volume -= 1
                        self.volume_disp.text = " "+str(self.volume)
                        mySong.duty = self.volume*2000 + 100


                display.render(self.icons)

            
                pass
            # Reset edge detection flags (reset finite state machine)
            B_rising_edge = False
            B_falling_edge = False
            
    def B1Handler(self,pin):
        global current_state, current_posx, current_posy
        if debounce_handler(pin):
            if(current_posx <= 0):
                current_posy-=1
                current_posx=0
            if(current_posy==0 and current_posx<=0):
                current_posx=3
                current_posy=5
            if(current_posx!=0):
                current_posx -= 1
            self.update()
            display.render(self.icons)
            
    def B2Handler(self,pin):
        pass
            
class PlayALARM(State):
    def __init__(self):
        super().__init__()
        self.ALARM = Icon("ALARM", 1, 2,True)
        self.Instructions1 = Icon("SNOOZE: CCW", 0,5,False)
        self.Instructions2 = Icon("OFF: CW", 0,0,False)
        self.icons = [self.ALARM, self.Instructions1, self.Instructions2]
        self.start_posx = 1
        self.start_posy = 0
    def update(self):
        display.update_buttons(self.icons)
    def B1Handler(self,pin):
        pass
    def B2Handler(self,pin):
        pass
    def ENCA(self,pin):
        global A_state, A_rising_edge, A_falling_edge, rotation_direction,current_state, Clock_s,SNOOZE, rtc, mySong
       
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
               change_state(Clock_s)
               year, month, day, weekday, hours, minutes, seconds, subseconds = rtc.datetime()
               if(minutes + Alarm_s.snoozeLength >= 60):
                   hours+=1
                   minutes = (minutes + Alarm_s.snoozeLength) % 60
                   SNOOZE = [year, month, day, weekday, hours, minutes, seconds, subseconds]
               else:
                   SNOOZE = [year, month, day, weekday, hours, minutes+Alarm_s.snoozeLength, seconds, subseconds]
    
            else:
               pass
            mySong.stop()
            # Reset edge detection flags
            A_rising_edge = False
            A_falling_edge = False
            
    # Interrupt handler for EncoderB pin (optional, if needed)
    def ENCB(self,pin):
        global B_state, B_rising_edge, B_falling_edge, rotation_direction, current_state,SNOOZE, mySong
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
                #DECREASE LOGIC
                change_state(Clock_s)
                SNOOZE = [0,0,0,0,0,0,0,0]
            mySong.stop()
            # Reset edge detection flags (reset finite state machine)
            B_rising_edge = False
            B_falling_edge = False
            
            
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

Clock_s = State()
Alarm_s = AlarmState()
Clock_s = ClockState()



Radio_s = RadioState()
Menu_s = MainMenuState()
#define states used by the clock radio before the clock radio
current_state = Menu_s
clock_radio = ClockRadio()
Playalarm_s = PlayALARM()

#    https://onlinesequencer.net/195547
song1 = '0 A#4 1 1;2 F5 1 1;4 D#5 1 1;8 D5 1 1;11 D5 1 1;6 A#4 1 1;14 D#5 1 1;18 A#4 1 1;20 D#5 1 1;22 A#4 1 1;24 D5 1 1;27 D5 1 1;30 D#5 1 1;32 A#4 1 1;34 F5 1 1;36 D#5 1 1;38 A#4 1 1;40 D5 1 1;43 D5 1 1;46 D#5 1 1;50 A#4 1 1;52 D#5 1 1;54 G5 1 1;56 F5 1 1;59 D#5 1 1;62 F5 1 1;64 A#4 1 1;66 F5 1 1;68 D#5 1 1;70 A#4 1 1;72 D5 1 1;75 D5 1 1;78 D#5 1 1;82 A#4 1 1;84 D#5 1 1;86 A#4 1 1;88 D5 1 1;91 D5 1 1;94 D#5 1 1;96 A#4 1 1;100 D#5 1 1;102 A#4 1 1;104 D5 1 1;107 D5 1 1;110 D#5 1 1;114 A#4 1 1;116 D#5 1 1;118 G5 1 1;120 F5 1 1;123 D#5 1 1;126 F5 1 1;98 F5 1 1'
#    https://onlinesequencer.net/1864273
song2 = '0 D5 4 14;4 A5 4 14;8 C6 4 14;12 B5 4 14;16 G5 2 14;18 F5 2 14;20 E5 2 14;22 F5 2 14;24 G5 8 14;4 E5 8 16;4 C5 8 16;4 F4 8 16;12 D5 8 16;12 B4 8 16;12 E4 8 16;20 C5 8 16;20 A4 8 16;20 D4 8 16;0 E4 4 16;0 B4 4 16;28 E4 4 16;28 B4 4 16'
#    https://onlinesequencer.net/1864297 - Tetris
song3 = '0 E3 1 0;2 E4 1 0;4 E3 1 0;6 E4 1 0;8 E3 1 0;10 E4 1 0;12 E3 1 0;14 E4 1 0;16 A3 1 0;18 A4 1 0;20 A3 1 0;22 A4 1 0;24 A3 1 0;26 A4 1 0;28 A3 1 0;30 A4 1 0;32 G#3 1 0;34 G#4 1 0;36 G#3 1 0;38 G#4 1 0;40 E3 1 0;42 E4 1 0;44 E3 1 0;46 E4 1 0;48 A3 1 0;50 A4 1 0;52 A3 1 0;54 A4 1 0;56 A3 1 0;58 B3 1 0;60 C4 1 0;62 D4 1 0;64 D3 1 0;66 D4 1 0;68 D3 1 0;70 D4 1 0;72 D3 1 0;74 D4 1 0;76 D3 1 0;78 D4 1 0;80 C3 1 0;82 C4 1 0;84 C3 1 0;86 C4 1 0;88 C3 1 0;90 C4 1 0;92 C3 1 0;94 C4 1 0;96 G2 1 0;98 G3 1 0;100 G2 1 0;102 G3 1 0;104 E3 1 0;106 E4 1 0;108 E3 1 0;110 E4 1 0;114 A4 1 0;112 A3 1 0;116 A3 1 0;118 A4 1 0;120 A3 1 0;122 A4 1 0;124 A3 1 0;0 E6 1 1;4 B5 1 1;6 C6 1 1;8 D6 1 1;10 E6 1 1;11 D6 1 1;12 C6 1 1;14 B5 1 1;0 E5 1 6;4 B4 1 6;6 C5 1 6;8 D5 1 6;10 E5 1 6;11 D5 1 6;12 C5 1 6;14 B4 1 6;16 A5 1 1;20 A5 1 1;22 C6 1 1;24 E6 1 1;28 D6 1 1;30 C6 1 1;32 B5 1 1;36 B5 1 1;36 B5 1 1;37 B5 1 1;38 C6 1 1;40 D6 1 1;44 E6 1 1;48 C6 1 1;52 A5 1 1;56 A5 1 1;20 A4 1 6;16 A4 1 6;22 C5 1 6;24 E5 1 6;28 D5 1 6;30 C5 1 6;32 B4 1 6;36 B4 1 6;37 B4 1 6;38 C5 1 6;40 D5 1 6;44 E5 1 6;48 C5 1 6;52 A4 1 6;56 A4 1 6;64 D5 1 6;64 D6 1 1;68 D6 1 1;70 F6 1 1;72 A6 1 1;76 G6 1 1;78 F6 1 1;80 E6 1 1;84 E6 1 1;86 C6 1 1;88 E6 1 1;92 D6 1 1;94 C6 1 1;96 B5 1 1;100 B5 1 1;101 B5 1 1;102 C6 1 1;104 D6 1 1;108 E6 1 1;112 C6 1 1;116 A5 1 1;120 A5 1 1;72 A5 1 6;80 E5 1 6;68 D5 1 7;70 F5 1 7;76 G5 1 7;84 E5 1 7;78 F5 1 7;86 C5 1 7;88 E5 1 6;96 B4 1 6;104 D5 1 6;112 C5 1 6;120 A4 1 6;92 D5 1 7;94 C5 1 7;100 B4 1 7;101 B4 1 7;102 C5 1 7;108 E5 1 7;116 A4 1 7'
songs = [song1, song2, song3]
mySong = music(songs[Alarm_s.song_id-1], pins=[Pin(26)])

def check_for_alarm():
    global current_state, current_posx, current_posy, Playalarm_s
    if((Alarm_s.alarm_hour==rtc.datetime()[4] and Alarm_s.alarm_minute == rtc.datetime()[5] and rtc.datetime()[6]==0  and Alarm_s.is_on=="Y") or (SNOOZE[0] == rtc.datetime()[0] and SNOOZE[1] == rtc.datetime()[1] and SNOOZE[2] == rtc.datetime()[2] and SNOOZE[3] == rtc.datetime()[3] and SNOOZE[4] == rtc.datetime()[4] and  SNOOZE[5] == rtc.datetime()[5] and SNOOZE[6] == rtc.datetime()[6])):
       change_state(Playalarm_s)
       mySong.resume()
while True:
    clock_radio.update(current_state)
    check_for_alarm()
    #play the alarm
    if(isinstance(current_state,PlayALARM)):
        radio.mute(True)
        radio.update_rds()
        mySong.tick()
        sleep(0.04)       
        if(Radio_s.is_on =="Y"):
            radio.mute(False)
            radio.update_rds()


