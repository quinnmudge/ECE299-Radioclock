from machine import Pin, SPI, I2C
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




frequency = 101.9


volume = 4
# Interrupt handler for EncoderA pin
def EncoderAInterrupt(pin):
    global A_state, A_rising_edge, A_falling_edge, rotation_direction
    
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
            return "Clockwise"
        else:
            return "Counter"
        
        # Reset edge detection flags
        A_rising_edge = False
        A_falling_edge = False
        
# Interrupt handler for EncoderB pin (optional, if needed)
def EncoderBInterrupt(pin):
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
            return "Clockwise"
        else:
            return "Counter"
        
        # Reset edge detection flags
        B_rising_edge = False
        B_falling_edge = False

# Attach interrupt handlers to EncoderA and EncoderB pins
EncoderA.irq(trigger=machine.Pin.IRQ_RISING | machine.Pin.IRQ_FALLING, handler=EncoderAInterrupt, hard = True)
EncoderB.irq(trigger=machine.Pin.IRQ_RISING | machine.Pin.IRQ_FALLING, handler=EncoderBInterrupt, hard = True)
grid_size_x = 42
grid_size_y = 10
ENTER = False
DEBOUNCE_DELAY_MS = 100

# Define button pins
button_1 = Pin(13, Pin.IN, Pin.PULL_DOWN)  # Button for moving left
button_2 = Pin(12, Pin.IN, Pin.PULL_DOWN)  # Button for moving right
enter = Pin(11, Pin.IN, Pin.PULL_DOWN)     # Button for enter

# Debouncing variables
last_pressed_time = 0
debounce_delay = DEBOUNCE_DELAY_MS // 2  # Adjusted for non-blocking debounce
class Radio:
    
    def __init__( self, NewFrequency, NewVolume, NewMute ):

#
# set the initial values of the radio
#
        self.Volume = 2
        self.Frequency = 88
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
        self.current_posx = 1
        self.current_posy = 0
        self.spi_sck = Pin(18)
        self.spi_sda = Pin(19)
        self.spi_res = Pin(16)
        self.spi_dc  = Pin(17)
        self.spi_cs  = Pin(20)
        SPI_DEVICE = 0
        self.oled_spi = SPI(SPI_DEVICE, baudrate=100000, sck=self.spi_sck, mosi=self.spi_sda)
        self.SSD = ssd1306.SSD1306_SPI(width, height, self.oled_spi, self.spi_dc, self.spi_res, self.spi_cs)
        self.SSD.fill(0)
        self.SSD.show()
        
    def update_buttons(self, icons):
        for icon in icons:
            if isinstance(icon, Button):
                if icon.grid_x == self.current_posx and icon.grid_y == self.current_posy:
                    icon.selected = True
                else:
                    icon.selected = False
               
    def render(self, icons):
        global ENTER, current_state
        self.update_buttons(icons)
        self.SSD.fill(0)
        for icon in icons:
            if isinstance(icon, Button) and icon.selected:
                self.SSD.fill_rect(icon.xpos_text - 2, icon.ypos_text - 2, icon.width, icon.height, 1)
                if ENTER and icon.state:
                    print("in")
                    print(icon.state)
                    current_state = icon.state  # Update current_state
                    
                    print(current_state)
                    ENTER = False  # Reset ENTER flag after handling
            else:
                self.SSD.text(icon.text, icon.xpos_text, icon.ypos_text)
                if icon.has_border:
                    self.SSD.rect(icon.xpos_text - 2, icon.ypos_text - 2, icon.width, icon.height, 1)
        self.SSD.show()

class State:
    def __init__(self):
        self.display = Display(128, 64)

class ClockState(State):
    def __init__(self, hour, minute):
        super().__init__()  # Initialize superclass Display
        self.current_hour = hour
        self.current_minute = minute
        #format clock string properly
        str_num = '{:02d}'.format(self.current_minute)
        clock = Icon((str(self.current_hour) + ":" + str_num),1,3,False)
        #add our clock icon to the list of icons to be displayed by the display
        self.icons = [clock]
    def render(self):
        self.display.render(self.icons)
        

class RadioState(State):
    def __init__(self):
        super().__init__()
        global frequency, radio
        _, _, frequency, _ = radio.GetSettings()
        self.frequency = Icon(str(frequency), 1, 3, True)
        self.icons = [self.frequency]

    def tune(self, pin):
        global rotation_direction, frequency,radio
        direction = EncoderAInterrupt(pin)
        if direction == "Clockwise":
            frequency += 0.1
        elif direction == "Counter":
            frequency -= 0.1
        if(radio.SetFrequency(frequency) ==True):
            radio.ProgramRadio()
        # Update the frequency displayed on the icon

    def render(self):
        global frequency
        self.frequency.text = f"{frequency:.1f}"
        self.display.render(self.icons)
        
        
        
class AlarmState(State):
    def render(self):
        print("Alarm")
        
class MainMenuState(State):
    def __init__(self):
        super().__init__()
        self.clock_but = Button("CLOCK", 1, 0, True, True)
        self.radio_but = Button("RADIO", 1, 2, False, True)
        self.alarm_but = Button("ALARM", 1, 4, False, True)
        self.clock_but.configureState(ClockState(12,1))
        self.radio_but.configureState(RadioState())
        self.alarm_but.configureState(AlarmState())
        self.menu = [self.radio_but, self.alarm_but, self.clock_but]

    def render(self):
        self.display.render(self.menu)

def debounce_handler(pin):
    global last_pressed_time
    current_time = utime.ticks_ms()
    if current_time - last_pressed_time < debounce_delay:
        return False
    last_pressed_time = current_time
    return pin.value() == 0  # Check if button is pressed

def B1_MainMenuHandler(pin):
    global current_state
    if debounce_handler(pin):
        current_state.display.current_posy -= 2

def B2_MainMenuHandler(pin):
    global current_state
    if debounce_handler(pin):
        current_state.display.current_posy += 2

def Enter_Handler(pin):
    global ENTER
    ENTER = True

class ClockRadio:
    def __init__(self):
        Radios= RadioState()
        button_1.irq(handler=B1_MainMenuHandler, trigger=Pin.IRQ_FALLING)
        button_2.irq(handler=B2_MainMenuHandler, trigger=Pin.IRQ_FALLING)
        EncoderA.irq(trigger=machine.Pin.IRQ_RISING | machine.Pin.IRQ_FALLING, handler=Radios.tune)
        enter.irq(handler=Enter_Handler, trigger=Pin.IRQ_FALLING)

    def update(self, state):
        state.render()
        
radio = Radio(101.9, 2, False)
clock_radio = ClockRadio()
current_state = MainMenuState()

while True:
    clock_radio.update(current_state)

