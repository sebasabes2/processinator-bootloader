//////////////////////////////////////////////////////////////////////////////
// Author: Sebastian Tobias Holdt
// Copyright: Technical University of Denmark - 2025
// Comments:
// This file contains the bootloader serial receiver running on the receiving computer
// It requires the implementations of the functions configUART, receiveChar, writeLEDs, jumpToAddress
//////////////////////////////////////////////////////////////////////////////

#include <stdint.h>

#define START_CODE (0x00017373U)
#define END_CODE (0x00027373U)

void configUART();
unsigned char receiveChar();
void writeLEDs(int bits);
void jumpToAddress(void *);

uint32_t nextWord() {
  uint32_t word = 0;
  for (int i = 0; i < 4; i ++) {
    word = (receiveChar() << 24) + (word >> 8); 
  }
  return word;
}

void main() {
  configUART();
  // Turn on LED to indicate bootloader state
  writeLEDs(1);
  // Wait on start code
  uint32_t code = 0;
  while (code != START_CODE) {
    code = (receiveChar() << 24) + (code >> 8);
  }
  // Write segments
  while (code != END_CODE) {
    unsigned char *writePointer = (unsigned char *)(uint64_t) nextWord();
    code = nextWord();
    while (code != START_CODE && code != END_CODE) {
      *writePointer = (unsigned char) (code & 0xff);
      writePointer ++;
      code = (receiveChar() << 24) + (code >> 8);
    }
  }
  // Get entry point
  uint64_t entryPoint = nextWord();
  // Turn off LEDs
  writeLEDs(0);
  // Jump to entry point
  jumpToAddress((void *) entryPoint);
}
