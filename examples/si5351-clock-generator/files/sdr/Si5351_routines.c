 #include <Si5351SDR.h>
// Si5351A commands///////////////////////////////
void sendRegister(char reg_addr, char reg_value){
  I2C1_Start();
  I2C1_Wr(SI5351A_ADDRESS);
  I2C1_Wr(reg_addr);
  I2C1_Wr(reg_value);
  I2C1_Stop();
}
void si5351aSetFrequency(unsigned long frequency){
        unsigned divider;
        unsigned long pllFreq;
        unsigned long xtalFreq = Si5351A_XTAL_FREQ;
        unsigned long l;
        float f;
        unsigned char mult;
        unsigned long num;
        unsigned long denom;
        if(frequency < 9050001)divider = 124;
        if(frequency > 9050000)divider = 44;
        pllFreq = divider * frequency;        // Calculate the pllFrequency: the divider * desired output frequency
        mult = pllFreq / xtalFreq;                // Determine the multiplier to get to the required pllFrequency
        l = pllFreq % xtalFreq;                        // It has three parts:
        f = l;                                                        // mult is an integer that must be in the range 15..90
        f *= 1048575;                                        // num and denom are the fractional parts, the numerator and denominator
        f /= xtalFreq;                                        // each is 20 bits (range 0..1048575)
        num = f;                                                // the actual multiplier is  mult + num / denom
        denom = 1048575;                                // For simplicity we set the denominator to the maximum 1048575
        setupPLL(SI_SYNTH_PLL_A, mult, num, denom);      // Set up PLL A with the calculated multiplication ratio
        setupMultisynth(SI_SYNTH_MS_0, divider, SI_R_DIV_1);
        setupMultisynth(SI_SYNTH_MS_1, divider, SI_R_DIV_1);
        sendRegister(CLK0_PHOFF,divider);
        sendRegister(CLK1_PHOFF, 0);
}
//////////////////////////////////////////////////////////////////////////////////////
void setupPLL(unsigned char pll, unsigned char mult, unsigned long num, unsigned long denom){
        unsigned long P1;                                        // PLL config register P1
        unsigned long P2;                                        // PLL config register P2
        unsigned long P3;                                        // PLL config register P3

        P1 = (unsigned long)(128 * ((float)num / (float)denom));
        P1 = (unsigned long)(128 * (unsigned long)(mult) + P1 - 512);
        P2 = (unsigned long)(128 * ((float)num / (float)denom));
        P2 = (unsigned long)(128 * num - denom * P2);
        P3 = denom;

        sendRegister(pll + 0, (P3 & 0x0000FF00) >> 8);
        sendRegister(pll + 1, (P3 & 0x000000FF));
        sendRegister(pll + 2, (P1 & 0x00030000) >> 16);
        sendRegister(pll + 3, (P1 & 0x0000FF00) >> 8);
        sendRegister(pll + 4, (P1 & 0x000000FF));
        sendRegister(pll + 5, ((P3 & 0x000F0000) >> 12) | ((P2 & 0x000F0000) >> 16));
        sendRegister(pll + 6, (P2 & 0x0000FF00) >> 8);
        sendRegister(pll + 7, (P2 & 0x000000FF));
}
//////////////////////////////////////////////////////////////////////////////////////
void setupMultisynth(unsigned char synth, unsigned long divider, unsigned char rDiv){
        unsigned long P1;                                        // Synth config register P1
        unsigned long P2;                                        // Synth config register P2
        unsigned long P3;                                        // Synth config register P3
        P1 = 128 * divider - 512;
        P2 = 0; // P2 = 0, P3 = 1 forces an integer value for the divider
        P3 = 1;
        sendRegister(synth + 0,   (P3 & 0x0000FF00) >> 8);
        sendRegister(synth + 1,   (P3 & 0x000000FF));
        sendRegister(synth + 2,   ((P1 & 0x00030000) >> 16) | rDiv);
        sendRegister(synth + 3,   (P1 & 0x0000FF00) >> 8);
        sendRegister(synth + 4,   (P1 & 0x000000FF));
        sendRegister(synth + 5,   ((P3 & 0x000F0000) >> 12) | ((P2 & 0x000F0000) >> 16));
        sendRegister(synth + 6,   (P2 & 0x0000FF00) >> 8);
        sendRegister(synth + 7,   (P2 & 0x000000FF));
}