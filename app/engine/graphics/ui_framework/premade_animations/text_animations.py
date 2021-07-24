from __future__ import annotations

import math
from typing import TYPE_CHECKING, Text, Union

from app.utilities.algorithms.interpolation import (lerp, log_interp)

if TYPE_CHECKING:
    from ..premade_components import TextComponent

from ..ui_framework_animation import InterpolationType, UIAnimation
from ..ui_framework_styling import UIMetric

"""
This file contains functions that will generate commonly used animations for text demand.
"""

def scroll_anim(start_scroll: Union[int, float, str, UIMetric], end_scroll: Union[int, float, str, UIMetric],
                duration: int=125, disable_after=False,
                interp_mode: InterpolationType = InterpolationType.LINEAR,
                skew: float = 10) -> UIAnimation:
    """A shorthand way of creating a scroll animation.

    Args:
        start_offset (Union[int, float, str, UIMetric]): Starting scroll
        end_offset (Union[int, float, str, UIMetric]): Ending scroll
        duration (int, optional): measured in milliseconds. How long the animation takes. Defaults to 125 (1/8 of a second)
        disable_after (bool, optional): whether or not to disable the component after the animation halts.
            Useful for transition outs.
        interp_mode (InterpolationType, optional): which interpolation strategy to use. Defaults to linear.
        skew (float, optional): if using InterpolationType.LOGARITHMIC, what skew to use for the interpolation

    Returns:
        UIAnimation: A UIAnimation that scrolls the TextComponent from one height to another
    """
    # convert scroll input
    if isinstance(start_scroll, str):
        sscroll = UIMetric.parse(start_scroll)
        escroll = UIMetric.parse(end_scroll)
    else:
        sscroll = start_scroll
        escroll = end_scroll

    if interp_mode == InterpolationType.LINEAR:
        lerp_func = lerp
    else:
        lerp_func = lambda a, b, t: log_interp(a, b, t, skew)

    def before_scroll(c: TextComponent, *args):
        c.set_scroll_height(sscroll)
    def do_scroll(c: TextComponent, anim_time, *args):
        c.set_scroll_height(lerp_func(sscroll, escroll, anim_time / duration))
    def after_translation(c: TextComponent, *args):
        c.set_scroll_height(escroll)
    def should_stop(c: TextComponent, anim_time, *args) -> bool:
        return anim_time >= duration

    def disable(c: TextComponent, *args):
        c.disable()

    if disable_after:
        return UIAnimation(halt_condition=should_stop, before_anim=before_scroll, do_anim=do_scroll, after_anim=[after_translation, disable])
    else:
        return UIAnimation(halt_condition=should_stop, before_anim=before_scroll, do_anim=do_scroll, after_anim=after_translation)

def scroll_to_next_line_anim(duration: int=500, disable_after=False,
                             interp_mode: InterpolationType = InterpolationType.LINEAR,
                             skew: float = 10):
    """A shorthand way of creating a scroll animation that scrolls to the next line

    Args:
        duration (int, optional): measured in milliseconds. How long the animation takes. Defaults to 125 (1/8 of a second)
        disable_after (bool, optional): whether or not to disable the component after the animation halts.
            Useful for transition outs.
        interp_mode (InterpolationType, optional): which interpolation strategy to use. Defaults to linear.
        skew (float, optional): if using InterpolationType.LOGARITHMIC, what skew to use for the interpolation

    Returns:
        UIAnimation: A UIAnimation that scrolls the TextComponent from one height to another
    """
    if interp_mode == InterpolationType.LINEAR:
        lerp_func = lerp
    else:
        lerp_func = lambda a, b, t: log_interp(a, b, t, skew)
    def do_scroll(c: TextComponent, anim_time, *args):
        original_line = math.floor(c.scrolled_line)
        next_line = original_line + 1
        c.set_scroll_height(lerp_func(original_line, next_line, anim_time / duration))
    def after_translation(c: TextComponent, *args):
        c.scroll_to_nearest_line()
    def should_stop(c: TextComponent, anim_time, *args) -> bool:
        return anim_time >= duration

    def disable(c: TextComponent, *args):
        c.disable()

    if disable_after:
        return UIAnimation(halt_condition=should_stop, do_anim=do_scroll, after_anim=[after_translation, disable])
    else:
        return UIAnimation(halt_condition=should_stop, do_anim=do_scroll, after_anim=after_translation)

def type_line_anim(time_per_char: int = 50, halting_sequence: str ='{w}'):
    def start_next_line(c: TextComponent, *args):
        # if we're at the stopped sequence, then let's just get over it
        if (c.is_index_at_sequence(c.num_visible_chars, halting_sequence)):
            c.num_visible_chars += len(halting_sequence)

    def type_next_character(c: TextComponent, anim_time, delta_time):
        # if enough time has passed since the last character has been typed
        type_next_character.time_since_last_char += delta_time
        while type_next_character.time_since_last_char > time_per_char:
            # as long as we haven't finished a line and we're not max lines:
            if ((not c.is_index_at_end_of_line(c.num_visible_chars) or c.lines_displayed != c.props.max_lines)
                    and not c.is_index_at_sequence(c.num_visible_chars, halting_sequence)):
                c.num_visible_chars += 1
                type_next_character.time_since_last_char -= time_per_char
            # we finished a line, and we're on the maximum line; it's time to scroll to make some space
            elif c.is_index_at_end_of_line(c.num_visible_chars) and not c.is_index_at_sequence(c.num_visible_chars, halting_sequence):
                c.push_animation([scroll_to_next_line_anim()])
                break
            else:
                break
    type_next_character.time_since_last_char = 0

    def halt(c: TextComponent, *args) -> bool:
        if (c.is_index_at_sequence(c.num_visible_chars, halting_sequence) or
                c.num_visible_chars == len(c.wrapped_text)):
            return True
        else:
            return False

    return UIAnimation(before_anim=start_next_line, do_anim=type_next_character, halt_condition=halt)
