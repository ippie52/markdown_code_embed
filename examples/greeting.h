/**
 * @file    greeting.h
 *
 * @brief   Prints a greeting to screen.
 *
 * @author  Kris Dunning (ippie52@gmail.com)
 * @date    2022
 */

#pragma once

/// @brief  Says hello to the name
/// @param  name    The name to greet
void sayHello(const char *name)
{
    printf("Hello, %s!\n", name);
}
