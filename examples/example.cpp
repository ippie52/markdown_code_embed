/**
 * @file    example.cpp
 *
 * @brief   Example C++ source file with simple functionality. Prints
 *          a greeting to the world, or the first argument passed.
 *
 * @author  Kris Dunning (ippie52@gmail.com)
 * @date    2022
 */

#include <cstdio>
#include "greeting.h"


// Entry point to the application
int main(int argc, char **argv)
{
    if (argc > 1)
    {
        sayHello(argv[1]);
    }
    else
    {
        sayHello("World");
    }
    return 0;
}
