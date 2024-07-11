from machine import Pin, SPI, I2C, RTC, Timer
import ssd1306
import utime
EncoderA = machine.Pin(27, machine.Pin.IN, machine.Pin.PULL_UP)
EncoderB = machine.Pin(28, machine.Pin.IN, machine.Pin.PULL_UP)

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
enter = Pin(11, Pin.IN, Pin.PULL_DOWN)     # Button for enter

# Debouncing variables
last_pressed_time = 0
debounce_delay = DEBOUNCE_DELAY_MS // 2  # Adjusted for non-blocking debounce

# RTC Setup
rtc = RTC()
rtc.datetime((2024, 7, 10, 0, 0, 0, 0, 0))  # Set initial RTC time (year, month, day, weekday, hours, minutes, seconds, subseconds)

# Clock State Class

class Radio:
    
    def __init__( self, NewFrequency, NewVolume, NewMute ):

#
# set the initial values of the radio
#
        self.Volume = 2
        self.Frequency = 101.9
        self.Mute = False
#
# Update the values with the ones passed in the initialization code
#
        self.SetVolume( NewVolume )
        self.SetFrequency( NewFrequency )
        self.SetMute( NewMute )
        
      
# Initialize I/O pins associated with the radio's I2C interface

        self.i2c_sda = Pin(0)
        self.i2c_scl = Pin(1)

#
# I2C Device ID can be 0 or 1. It must match the wiring. 
#
# The radio is connected to device number 1 of the I2C device
#
        self.i2c_device = 0 
        self.i2c_device_address = 0x10

#
# Array used to configure the radio
#
        self.Settings = bytearray( 8 )


        self.radio_i2c = I2C( self.i2c_device, scl=self.i2c_scl, sda=self.i2c_sda, freq=200000)
        self.ProgramRadio()

    def SetVolume( self, NewVolume ):
#
# Conver t the string into a integer
#
        try:
            NewVolume = int( NewVolume )
            
        except:
            return( False )
        
#
# Validate the type and range check the volume
#
        if ( not isinstance( NewVolume, int )):
            return( False )
        
        if (( NewVolume < 0 ) or ( NewVolume >= 16 )):
            return( False )

        self.Volume = NewVolume
        return( True )



    def SetFrequency( self, NewFrequency ):
#
# Convert the string into a floating point value
#
        try:
            NewFrequency = float( NewFrequency )
            
        except:
            return( False )
#
# validate the type and range check the frequency
#
        if ( not ( isinstance( NewFrequency, float ))):
            return( False )
 
        if (( NewFrequency < 88.0 ) or ( NewFrequency > 108.0 )):
            return( False )

        self.Frequency = NewFrequency
        return( True )
        
    def SetMute( self, NewMute ):
        
        try:
            self.Mute = bool( int( NewMute ))
            
        except:
            return( False )
        
        return( True )

#
# convert the frequency to 10 bit value for the radio chip
#
    def ComputeChannelSetting( self, Frequency ):
        Frequency = int( Frequency * 10 ) - 870
        
        ByteCode = bytearray( 2 )
#
# split the 10 bits into 2 bytes
#
        ByteCode[0] = ( Frequency >> 2 ) & 0xFF
        ByteCode[1] = (( Frequency & 0x03 ) << 6 ) & 0xC0
        return( ByteCode )

#
# Configure the settings array with the mute, frequency and volume settings
#
    def UpdateSettings( self ):
        
        if ( self.Mute ):
            self.Settings[0] = 0x80
        else:
            self.Settings[0] = 0xC0
  
        self.Settings[1] = 0x09 | 0x04
        self.Settings[2:3] = self.ComputeChannelSetting( self.Frequency )
        self.Settings[3] = self.Settings[3] | 0x10
        self.Settings[4] = 0x04
        self.Settings[5] = 0x00
        self.Settings[6] = 0x84
        self.Settings[7] = 0x80 + self.Volume

#        
# Update the settings array and transmitt it to the radio
#
    def ProgramRadio( self ):

        self.UpdateSettings()
        self.radio_i2c.writeto( self.i2c_device_address, self.Settings )

#
# Extract the settings from the radio registers
#
    def GetSettings( self ):
#        
# Need to read the entire register space. This is allow access to the mute and volume settings
# After and address of 255 the 
#
        self.RadioStatus = self.radio_i2c.readfrom( self.i2c_device_address, 256 )

        if (( self.RadioStatus[0xF0] & 0x40 ) != 0x00 ):
            MuteStatus = False
        else:
            MuteStatus = True
            
        VolumeStatus = self.RadioStatus[0xF7] & 0x0F
 
 #
 # Convert the frequency 10 bit count into actual frequency in Mhz
 #
        FrequencyStatus = (( self.RadioStatus[0x00] & 0x03 ) << 8 ) | ( self.RadioStatus[0x01] & 0xFF )
        FrequencyStatus = ( FrequencyStatus * 0.1 ) + 87.0
        
        if (( self.RadioStatus[0x00] & 0x04 ) != 0x00 ):
            StereoStatus = True
        else:
            StereoStatus = False
        
        return( MuteStatus, VolumeStatus, FrequencyStatus, StereoStatus )
    
    
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
                        print("in")
                        current_state = icon.state
                        current_posx = current_state.start_posx
                        current_posy = current_state.start_posy
                        button_1.irq(handler=current_state.B1Handler, trigger=Pin.IRQ_FALLING)
                        button_2.irq(handler=current_state.B2Handler, trigger=Pin.IRQ_FALLING)
                        if(not(isinstance(current_state,MainMenuState))):
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

class ClockState(State):
    def __init__(self):
        super().__init__()  # Initialize superclass Display
        self.menu = Button("Menu",0,5,True,True)
        self.menu.configureState(Menu_s)
        self.hour_adj = Button("Hr.",1,5,False,True)
        self.min_adj = Button("Min",2,5,False,True)
        self.format_time = "12h"
        self.format_adj = Button(self.format_time,0,0,False,True)
        self.zone = "PST"
        self.time_zone = Button(self.zone,1,0,False,True)
        self.start_posx = 0
        self.start_posy = 5
        self.clock = Icon("", 1, 3, False)  # Placeholder for the clock icon
        self.update_time()  # Initialize the clock display
        self.icons = [self.clock, self.menu, self.hour_adj, self.min_adj,self.format_adj,self.time_zone]
        # Timer setup for minute update
        self.timer = Timer()
        self.timer.init(period=60000, mode=Timer.PERIODIC, callback=self.timer_callback)
        
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

    def update_time(self):
        year, month, day, weekday, hours, minutes, seconds, subseconds = rtc.datetime()
        
        if(self.format_time=="24h"):
            clock_text = '{:02d}:{:02d}'.format(hours, minutes)
        else:
            clock_text = self.convert_to_12h(hours,minutes)

        self.clock.text = clock_text
    def update(self):
        self.menu.configureState(Menu_s)
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
#    def B2Handler(self,pin):
#         global current_state, current_posy
#         if debounce_handler(pin):
#             current_posy += 2
#             
#             if(current_posy >4):
#                 current_posy = 4
#                 
#             self.update()
#             display.render(self.icons)
            
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
                    print("in")
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
                    print("in")
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
        self.volume = 4
        self.frequ_disp = Button(str(self.freq), 1, 3,False, True)
        self.menu = Button("Menu",0,5,True,True)
        self.menu.configureState(Menu_s)
        self.vol_adj = Button("Vol.",1,5,False,True)
        self.vol_disp = Icon(str(self.volume),0,1,False)
        self.freq_adj = Button("Freq.",2,5,False,True)
        self.icons = [self.frequ_disp, self.menu, self.vol_adj, self.freq_adj,self.vol_disp]
        self.start_posx = 0
        self.start_posy = 5
   
    def update(self):
        self.menu.configureState(Menu_s)
        display.update_buttons(self.icons)
        
    def ENCA(self,pin):
        global A_state, A_rising_edge, A_falling_edge, rotation_direction, radio
        print("in")
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
                    if(radio.SetFrequency(self.freq +0.1) ==True):
                       self.freq +=0.1
                       radio.ProgramRadio()
                    # Update the frequency displayed on the icon
                       self.frequ_disp.text = f"{self.freq:.1f}"
                       display.render(self.icons)
                if(self.vol_adj.selected):
                    if ( radio.SetVolume(self.volume+1 ) == True ):
                        radio.ProgramRadio()
                        self.volume+=1
                        self.vol_disp.text = str(self.volume)
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
                    if(radio.SetFrequency(self.freq-0.1) ==True):
                        self.freq-=0.1
                        radio.ProgramRadio()
                    # Update the frequency displayed on the icon
                        self.frequ_disp.text = f"{self.freq:.1f}"
                        display.render(self.icons)
                if(self.vol_adj.selected):
                    if ( radio.SetVolume( self.volume-1 ) == True ):
                            radio.ProgramRadio()
                            self.volume-=1
                            self.vol_disp.text = str(self.volume)
                            display.render(self.icons)
                
            # Reset edge detection flags
            B_rising_edge = False
            B_falling_edge = False
 
    def B1Handler(self,pin):
        global current_posx
        if debounce_handler(pin):
            current_posx +=1
            if(current_posx>2):
                current_posx = 2
            self.update()
        
            display.render(self.icons)
           
    def B2Handler(self,pin):
        global current_posx
        if debounce_handler(pin):
            current_posx-=1
            if(current_posx<0):
                current_posx = 0
            self.update()
            display.render(self.icons)
            
      
class AlarmState(State):
    def __init__(self):
        super().__init__()
        global rtc
        self.alarm_text = Icon("Alarm:",0,3,False)
        self.snooze_text = Icon("Sleep:",0,4,False)
        self.frequency_text = Icon("Freq:",0,2,False)
        self.start_posx = 0
        self.start_posy = 5
        self.snoozeLength = 5
        self.alarm_hour = 0
        self.alarm_minute = 0
        str_num = '{:02d}'.format(self.alarm_minute)
        self.alarm_disp = Icon(" "+str(self.alarm_hour)+":"+str_num,1,3,False)
        self.snooze_disp = Icon(" 15" + " Mins",1,4,False)
        self.frequency_disp = Icon(" 500Hz",1,2,False)
        self.hour_adj = Button("Hr.",1,5,False,True)
        self.minute_adj = Button("Min.",2,5,False,True)
        self.snooze_adj = Button("Sleep",0,0,False,True)
        self.menu = Button("Menu",0,5,True,True)
        self.menu.configureState(Menu_s)
        self.is_on = "N"
        self.alarmOn = Button("On: " + self.is_on,1,0,False,True)
        self.alarmconfig = Button("Tune",2,0,False,True)
        self.icons = [self.alarm_text,self.snooze_text,self.alarm_disp,self.snooze_disp,self.hour_adj,self.minute_adj,self.snooze_adj,self.menu,self.alarmOn,self.alarmconfig,self.frequency_text,self.frequency_disp]
        
    def update(self):
        self.menu.configureState(Menu_s)
        display.update_buttons(self.icons)
    def ENCA(self,pin):
        global A_state, A_rising_edge, A_falling_edge, rotation_direction, radio
        print("in")
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
              #INCREASE LOGIC
                pass
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
                pass
            # Reset edge detection flags (reset finite state machine)
            B_rising_edge = False
            B_falling_edge = False
            
    def B1Handler(self,pin):
        global current_state, current_posx, current_posy
        if debounce_handler(pin):
            if(current_posx <= 0 and current_posy ==5):
                current_posy=0
                current_posx = 2
            elif(current_posx<=0 and current_posy ==0):
                current_posy=5
                current_posx=2
            else:
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
    def update(self):
        display.update_buttons(self.icons)
    def B1Handler(self,pin):
        pass
    def B2Handler(self,pin):
        pass
    def ENCA(self,pin):
        global A_state, A_rising_edge, A_falling_edge, rotation_direction, snooze
        print("in")
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
              #INCREASE LOGIC
                snooze = True
            else:
               pass
            
            # Reset edge detection flags
        A_rising_edge = False
        A_falling_edge = False
            
    # Interrupt handler for EncoderB pin (optional, if needed)
    def ENCB(self,pin):
        global B_state, B_rising_edge, B_falling_edge, rotation_direction, Alarm_s
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
                current_state = Clock_s
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
                current_posy = 0
            self.update()
            display.render(self.icons)
    def B2Handler(self,pin):
        global current_state, current_posy
        if debounce_handler(pin):
            current_posy += 2
            if(current_posy >4):
                current_posy = 4
            self.update()
            display.render(self.icons)

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

class ClockRadio:
    def __init__(self):
        global Radio_s, current_state
        button_1.irq(handler=current_state.B1Handler, trigger=Pin.IRQ_FALLING)
        button_2.irq(handler=current_state.B2Handler, trigger=Pin.IRQ_FALLING)
        EncoderA.irq(trigger=machine.Pin.IRQ_RISING | machine.Pin.IRQ_FALLING, handler=Radio_s.ENCA)
        EncoderB.irq(trigger=machine.Pin.IRQ_RISING | machine.Pin.IRQ_FALLING, handler=Radio_s.ENCB)
        enter.irq(handler=Enter_Handler, trigger=Pin.IRQ_FALLING)

    def update(self, state):
        state.update()
        check_for_alarm()
        pass
     
    
display = Display(128,64)

radio = Radio(101.9, 15, False)
radio.SetMute(False)
radio.ProgramRadio()
Menu_s = None

Clock_s = ClockState()

Alarm_s = AlarmState()

Radio_s = RadioState()
Menu_s = MainMenuState()
#define states used by the clock radio before the clock radio
current_state = Menu_s
clock_radio = ClockRadio()
Playalarm_s = PlayALARM()
def check_for_alarm():
    if(Alarm_s.alarm_hour==rtc.datetime()[4] and Alarm_s.alarm_minute == rtc.datetime()[5]):
        current_state = Playalarm_s

while True:
    clock_radio.update(current_state)
    print(radio.Frequency)
    



