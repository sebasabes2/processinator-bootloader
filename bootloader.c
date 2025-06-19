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
#define ZERO_CODE (0x00037373U)

struct ZeroSection {
  void *startPointer;
  uint64_t size; 
};

void configUART();
uint8_t receiveChar();
void writeLEDs(int bits);
void jumpToAddress(void *);

uint32_t nextWord() {
  uint32_t word = 0;
  for (int i = 0; i < 4; i ++) {
    word = (receiveChar() << 24) + (word >> 8); 
  }
  return word;
}

void writeByte(volatile uint8_t *writePointer, uint8_t byte) {
  *writePointer = byte;
}

void writeDoubleWord(volatile uint64_t *writePointer, uint64_t doubleWord) {
  *writePointer = doubleWord;
}

void main() {
  struct ZeroSection zeroSections[32];
  int zeroI = 0;
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
    if (code == START_CODE) {
      uint8_t *writePointer = (uint8_t *)(uint64_t) nextWord();
      code = nextWord();
      while (code != START_CODE && code != END_CODE && code != ZERO_CODE) {
        writeByte(writePointer, (uint8_t) (code & 0xff));
        writePointer ++;
        code = (receiveChar() << 24) + (code >> 8);
      }
    }
    if (code == ZERO_CODE) {
      zeroSections[zeroI].startPointer = (uint8_t *)(uint64_t) nextWord();
      zeroSections[zeroI].size = (uint64_t) nextWord();
      zeroI++;
      code = nextWord();
    }
  }
  // Get entry point
  uint64_t entryPoint = nextWord();
  // ZeroSections
  while (zeroI != 0) {
    zeroI--;
    void *writePointer = zeroSections[zeroI].startPointer;
    void *endPointer = zeroSections[zeroI].startPointer + zeroSections[zeroI].size;
    while (writePointer + 7 < endPointer) {
      writeDoubleWord(writePointer, 0);
      writePointer += 8;
    }
    while (writePointer < endPointer) {
      writeByte(writePointer, 0);
      writePointer++;
    }
  }
  // Turn off LEDs
  writeLEDs(0);
  // Jump to entry point
  jumpToAddress((void *) entryPoint);
}
