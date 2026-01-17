///////////////////////////////////////////
#define SSD1306_128_32
#define SI5351A_ADDRESS        0xC0
#define Si5351A_XTAL_FREQ      24999117
#define SI_CLK0_CONTROL        16
#define SI_CLK1_CONTROL        17
#define SI_CLK2_CONTROL        18
#define SI_SYNTH_PLL_A         26
#define SI_SYNTH_PLL_B         34
#define SI_SYNTH_MS_0          42
#define SI_SYNTH_MS_1          50
#define SI_SYNTH_MS_2          58
#define SI_PLL_RESET           177
#define SI_R_DIV_1             0b00000000
#define SI_R_DIV_2             0b00010000
#define SI_R_DIV_4             0b00100000
#define SI_R_DIV_8             0b00110000
#define SI_R_DIV_16            0b01000000
#define SI_R_DIV_32            0b01010000
#define SI_R_DIV_64            0b01100000
#define SI_R_DIV_128           0b01110000
#define SI_CLK_SRC_PLL_A       0b00000000
#define SI_CLK_SRC_PLL_B       0b00100000
#define CLK_ENABLE_CONTROL     3
#define PLLX_SRC               15
#define XTAL_LOAD_CAP          183
#define CLK0_PHOFF             165
#define CLK1_PHOFF             166
/////////////////////////////////////////////////
#define print_USB              SSD1306_TextSize(1); SSD1306_GotoXY(1,4); SSD1306_Print("USB"); SSD1306_Display();
#define print_LSB              SSD1306_TextSize(1); SSD1306_GotoXY(1,4); SSD1306_Print("LSB"); SSD1306_Display();
#define print_AM               SSD1306_TextSize(1); SSD1306_GotoXY(1,4); SSD1306_Print("AM "); SSD1306_Display();
#define print_1KHz             SSD1306_TextSize(1); SSD1306_GotoXY(91,4); SSD1306_Print("  1KHz"); SSD1306_Display();
#define print_100Hz            SSD1306_TextSize(1); SSD1306_GotoXY(91,4); SSD1306_Print(" 100Hz"); SSD1306_Display();
#define print_10Hz             SSD1306_TextSize(1); SSD1306_GotoXY(91,4); SSD1306_Print("  10Hz"); SSD1306_Display();
#define print_5KHz             SSD1306_TextSize(1); SSD1306_GotoXY(91,4); SSD1306_Print("  5KHz"); SSD1306_Display();
#define print_100KHz           SSD1306_TextSize(1); SSD1306_GotoXY(91,4); SSD1306_Print("100KHz"); SSD1306_Display();
#define print_1Hz              SSD1306_TextSize(1); SSD1306_GotoXY(91,4); SSD1306_Print("   1Hz"); SSD1306_Display();
#define StepSW                 porta.b3
#define ModeSW                 porta.b4
#define AMSel                  portc = 0x00
#define USBSel                 portc = 0x10
#define LSBSel                 portc = 0x20
#define EncodIn               (porta & 0x03)
/////////////////variables/////////////////////
extern unsigned long freq;
extern unsigned long StepVal;
extern char LCDText[15];
extern char StepCnt;
extern char ModeCnt;
//////////////////////////////////////////////
void si5351aOutputOff (unsigned char);
void si5351aSetFrequency (unsigned long);
void setupPLL (unsigned char, unsigned char, unsigned long, unsigned long);
void setupMultisynth (unsigned char, unsigned long, unsigned char);
void sendRegister (unsigned char, unsigned char);
//////////////////////////////////////////////
void SelectMode(void);
unsigned long SelectStep(void);
void DisplayFreq(void);
char Controls();