from machine import Pin, SPI, I2C, RTC, Timer, PWM
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
current_posy = 0
# Interrupt handler for EncoderA pin

grid_size_x = 42
grid_size_y = 10
ENTER = False
LAST_ENTER = False
DEBOUNCE_DELAY_MS = 100

# Define button pins
button_1 = Pin(13, Pin.IN, Pin.PULL_DOWN)  # Button for moving left
button_2 = Pin(12, Pin.IN, Pin.PULL_DOWN)  # Button for moving right
enter = Pin(5, Pin.IN, Pin.PULL_DOWN)     # Button for enter

# Debouncing variables
last_pressed_time = 0
debounce_delay = DEBOUNCE_DELAY_MS // 2  # Adjusted for non-blocking debounce
radio_programming_timer = utime.ticks_ms()
# RTC Setup
rtc = RTC()
rtc.datetime((2024, 7, 10, 0, 0, 0, 0, 0))  # Set initial RTC time (year, month, day, weekday, hours, minutes, seconds, subseconds)
SNOOZE = -1


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
                        current_posx = current_state.start_posx
                        current_posy = current_state.start_posy
                        button_1.irq(handler=current_state.B1Handler, trigger=Pin.IRQ_FALLING)
                        button_2.irq(handler=current_state.B2Handler, trigger=Pin.IRQ_FALLING)
                        EncoderA.irq(trigger=machine.Pin.IRQ_RISING | machine.Pin.IRQ_FALLING, handler=current_state.ENCA)
                        EncoderB.irq(trigger=machine.Pin.IRQ_RISING | machine.Pin.IRQ_FALLING, handler=current_state.ENCB)
                        self.render(current_state.icons)
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
    def B2Handler(pin):
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
        self.zone = 7
        self.zone = "UTC"+str(self.zone)
        self.time_zone = Button(self.zone,1,0,False,True)
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
        self.Alarm_on.text = "Al: " +Alarm_s.is_on
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
        global A_state, A_rising_edge, A_falling_edge, rotation_direction, radio, rtc
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
                if self.hour_adj.selected:
                    year, month, day, weekday, hours, minutes, seconds, subseconds = rtc.datetime()
                    if hours+1<=23:
                        print(self.timer)
                        rtc.datetime((year, month, day, weekday, (hours+1), minutes, seconds, subseconds))
                    else:
                        pass
                if self.min_adj.selected:
                    year, month, day, weekday, hours, minutes, seconds, subseconds = rtc.datetime()
                    if minutes+1<=59:
                        rtc.datetime((year, month, day, weekday, hours, (minutes+1), seconds, subseconds))
                    else:
                        pass
                if self.format_adj.selected:
                  
                    if(self.format_time =="24h"):
                        self.format_time = "12h"
                    else:
                        self.format_time = "24h"
                    self.format_adj.text = self.format_time
            else:
                pass
            
            # Reset edge detection flags
            A_rising_edge = False
            A_falling_edge = False
            self.update_time()
            display.render(self.icons)

    # Interrupt handler for EncoderB pin (optional, if needed)
    def ENCB(self, pin):
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
                if self.hour_adj.selected:
                    year, month, day, weekday, hours, minutes, seconds, subseconds = rtc.datetime()
                    if hours-1>=0 :
                        rtc.datetime((year, month, day, weekday, (hours-1), minutes, seconds, subseconds))
                    else:
                        pass
                   
                if self.min_adj.selected:
                    year, month, day, weekday, hours, minutes, seconds, subseconds = rtc.datetime()
                    if minutes -1>=0:
                        rtc.datetime((year, month, day, weekday, hours, (minutes-1), seconds, subseconds))
                    else:
                        pass
                if self.format_adj.selected:
                   
                    if(self.format_time =="24h"):
                        self.format_time = "12h"
                    else:
                        self.format_time = "24h"
                        
                    self.format_adj.text = self.format_time
                      
                
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
        self.volume = 3
        self.is_on = "N"
        self.radioOn = Button("On: " + self.is_on,1,0,False,True)
        self.frequency_text = Icon("Freq:",0,3,False)
        self.volume_text = Icon("Volume:",0,2,False)
        self.frequ_disp = Button("  "+str(self.freq)+"FM", 1, 3,False, False)
        self.menu = Button("Menu",0,5,True,True)
        self.menu.configureState(Menu_s)
        self.vol_adj = Button("Vol.",1,5,False,True)
        self.vol_disp = Icon(str(self.volume),2,2,False)
        self.freq_adj = Button("Freq.",2,5,False,True)
        self.icons = [self.frequ_disp, self.menu, self.vol_adj, self.freq_adj,self.vol_disp,self.frequency_text, self.volume_text,self.radioOn]
        self.start_posx = 0
        self.start_posy = 5
   
    def update(self):
        self.menu.configureState(Menu_s)
        display.update_buttons(self.icons)
        
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
                   radio.set_frequency_MHz(self.freq +0.1)
                   self.freq +=0.1
                   radio.update_rds()
                   # Update the frequency displayed on the icon
                   self.frequ_disp.text = "  "+f"{self.freq:.1f}"+"FM"
                if(self.vol_adj.selected):
                    if(self.volume+1 <=15): 
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
                    radio.set_frequency_MHz(self.freq-0.1)
                    self.freq-=0.1
                    radio.update_rds()
                    # Update the frequency displayed on the icon
                    self.frequ_disp.text = "  "+f"{self.freq:.1f}"+"FM"
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
                display.render(self.icons)
                
            # Reset edge detection flags
            B_rising_edge = False
            B_falling_edge = False
 
    def B1Handler(self,pin):
        global current_posx, current_posy
        if debounce_handler(pin):
            current_posx -=1
            if(current_posx<0):
                current_posx = 1
                current_posy = 0
            if(current_posx==0 and current_posy ==0):
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
        self.alarmOn = Button("Alarm:",0,4,False,True)
        self.snooze_adj = Button("Sleep:",0,3,False,True)
        self.frequency_adj = Button("Freq:",0,2,False,True)
        self.volume_adj = Button("Vol:",0,1,False,True)
        self.volume = 1
        self.start_posx = 0
        self.start_posy = 5
        self.snoozeLength = 5
        self.alarm_hour = 0
        self.alarm_minute = 0
        self.frequency = 1000
        str_num = '{:02d}'.format(self.alarm_minute)
        self.volume_disp = Icon(" "+str(self.volume),1,1,False)
        self.alarm_disp = Icon(" "+str(self.alarm_hour)+":"+str_num,1,4,False)
        self.snooze_disp = Icon(" "+str(self.snoozeLength) + " Mins",1,3,False)
        self.frequency_disp = Icon(" " + str(self.frequency)+"Hz",1,2,False)
        self.hour_adj = Button("Hr.",1,5,False,True)
        self.minute_adj = Button("Min.",2,5,False,True)
        self.menu = Button("Menu",0,5,True,True)
        self.menu.configureState(Menu_s)
        self.is_on = "N"
        self.alarm_on = Icon("On: " + self.is_on,2,0,False)
        self.icons = [self.alarm_on,self.volume_disp,self.alarm_disp,self.snooze_disp,self.hour_adj,self.minute_adj,self.menu,self.alarmOn,self.frequency_adj,self.frequency_disp,self.snooze_adj, self.volume_adj]
        
    def update(self):
        self.menu.configureState(Menu_s)
        display.update_buttons(self.icons)

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
                if(self.frequency_adj.selected):
                    if(self.frequency+10 <= 10000):
                        self.frequency +=10
                        # Update the frequency displayed on the icon
                        self.frequency_disp.text = " " + str(self.frequency)+"Hz"
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

                display.render(self.icons)
            else:
                pass
            
            # Reset edge detection flags
            A_rising_edge = False
            A_falling_edge = False        
    # Interrupt handler for EncoderB pin (optional, if needed)
    def ENCB(self,pin):
        global B_state, B_rising_edge, B_falling_edge, rotation_direction
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
                if(self.frequency_adj.selected):
                    if(self.frequency-10 >= 0):
                       self.frequency -=10
                    # Update the frequency displayed on the icon
                       self.frequency_disp.text = " " + str(self.frequency)+"Hz"
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
                display.render(self.icons)

            
                pass
            # Reset edge detection flags (reset finite state machine)
            B_rising_edge = False
            B_falling_edge = False
            
    def B1Handler(self,pin):
        global current_state, current_posx, current_posy
        if debounce_handler(pin):
            if(current_posx <= 0):
                print("in")
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
        self.icons = [self.ALARM]
        self.start_posx = 1
        self.start_posy = 0
    def update(self):
        display.update_buttons(self.icons)
    def B1Handler(self,pin):
        pass
    def B2Handler(self,pin):
        pass
    def ENCA(self,pin):
        global A_state, A_rising_edge, A_falling_edge, rotation_direction,current_state, Clock_s,SNOOZE
       
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
               SNOOZE = utime.ticks_ms()
               print(SNOOZE)
               print("should set snooze")
    
            else:
               pass
            
            # Reset edge detection flags
            A_rising_edge = False
            A_falling_edge = False
            
    # Interrupt handler for EncoderB pin (optional, if needed)
    def ENCB(self,pin):
        global B_state, B_rising_edge, B_falling_edge, rotation_direction, current_state,SNOOZE
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
                SNOOZE = -1
            # Reset edge detection flags (reset finite state machine)
            B_rising_edge = False
            B_falling_edge = False
            
            
class MainMenuState(State):
    def __init__(self):
        super().__init__()
        global icons
        self.clock_but = Button("CLOCK", 1, 0, True, True)
        self.radio_but = Button("RADIO", 1, 2, False, True)
        self.alarm_but = Button("ALARM", 1, 4, False, True)
        self.clock_but.configureState(Clock_s)
        self.radio_but.configureState(Radio_s)
        self.alarm_but.configureState(Alarm_s)
        self.icons = [self.radio_but, self.alarm_but, self.clock_but]
        self.start_posx = 1
        self.start_posy = 0
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
    def B2Handler(self,pin):
        pass

def debounce_handler(pin):
    global last_pressed_time
    current_time = utime.ticks_ms()
    if current_time - last_pressed_time < debounce_delay:
        return False
    last_pressed_time = current_time
    return pin.value() == 0  # Check if button is pressed


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
    button_2.irq(handler=current_state.B2Handler, trigger=Pin.IRQ_FALLING)
    current_state.update()
    display.render(current_state.icons)
class ClockRadio:
    def __init__(self):
        global Radio_s, current_state
        button_1.irq(handler=current_state.B1Handler, trigger=Pin.IRQ_FALLING)
        button_2.irq(handler=current_state.B2Handler, trigger=Pin.IRQ_FALLING)
        EncoderA.irq(trigger=machine.Pin.IRQ_RISING | machine.Pin.IRQ_FALLING, handler=Radio_s.ENCA)
        EncoderB.irq(trigger=machine.Pin.IRQ_RISING | machine.Pin.IRQ_FALLING, handler=Radio_s.ENCB)
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

def check_for_alarm():
    global current_state, current_posx, current_posy, Playalarm_s
    if((Alarm_s.alarm_hour==rtc.datetime()[4] and Alarm_s.alarm_minute == rtc.datetime()[5] and Alarm_s.is_on=="Y") or (utime.ticks_diff(utime.ticks_ms(),SNOOZE) > Alarm_s.snoozeLength * 60000) and SNOOZE >0):
       print("should play alarm")
       change_state(Playalarm_s)
while True:
    clock_radio.update(current_state)
    check_for_alarm()
    #play the alarm
    if(isinstance(current_state,PlayALARM)):
        radio.mute(True)
        radio.update_rds()
        pwm = PWM(Pin(26))
        # Set the frequency of the PWM signal
        count=0
        while(count<2):
            pwm.freq(Alarm_s.frequency)
        # Set the duty cycle to 50% (range is 0 to 65535, so 32767 is 50%)
            pwm.duty_u16(Alarm_s.volume*8100 + 100)
        # Wait for 0.5 seconds
            utime.sleep(0.5)
            pwm.duty_u16(0)
            utime.sleep(0.5)
            count+=1
        if(Radio_s.is_on =="Y"):
            radio.mute(False)
            radio.update_rds()
        # Turn off the PWM signal by setting the duty cycle to 0
        pwm.duty_u16(0)
        
        # Deinitialize the PWM to free up the GPIO pin
        pwm.deinit()
        
        
        
        

    



