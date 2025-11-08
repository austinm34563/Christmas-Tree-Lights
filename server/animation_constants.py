
from enum import Enum
from animation import *

class AnimationId(Enum):
    CycleFade=1
    Fade=2
    Blink=3
    Chase=4
    TwinkleStars=5
    CandleFlicker=6
    Bouncing=7
    Twinkle=8
    TwinkleCycle=9
    Cover=10
    Cylon=11
    RainbowWave=12
    SparkleGlitter=13
    BurstingSparkle=14
    Fireworks=15

ANIMATIONS = {
    "Cycle Fade": {
        "id": AnimationId.CycleFade.value,
        "description": "Gradually fades through a cycle of colors in a smooth transition."
    },
    "Fade": {
        "id": AnimationId.Fade.value,
        "description": "Fades LEDs in and out through a specified set of colors."
    },
    "Blink": {
        "id": AnimationId.Blink.value,
        "description": "Alternates LEDs between colors in color palette in a blinking pattern."
    },
    "Chase": {
        "id": AnimationId.Chase.value,
        "description": "Creates a chasing light effect where a color moves across the LEDs."
    },
    "Twinkle Stars": {
        "id": AnimationId.TwinkleStars.value,
        "description": "Simulates a starry night with LEDs twinkling at random intervals."
    },
    "Candle Flicker": {
        "id": AnimationId.CandleFlicker.value,
        "description": "Mimics the natural flicker of a candle flame with subtle brightness variations."
    },
    "Bouncing": {
        "id": AnimationId.Bouncing.value,
        "description": "Creates a bouncing light effect as if a ball is moving across the LEDs."
    },
    "Twinkle": {
        "id": AnimationId.Twinkle.value,
        "description": "Randomly twinkles individual LEDs with subtle fades on and off."
    },
    "Twinkle Cycle": {
        "id": AnimationId.TwinkleCycle.value,
        "description": "Combines twinkling with a color cycling effect."
    },
    "Cover": {
        "id": AnimationId.Cover.value,
        "description": "Simulates a sweeping cover effect where LEDs turn on sequentially."
    },
    "Cylon": {
        "id": AnimationId.Cylon.value,
        "description": "Moving lights that fade as they move forward."
    },
    "Rainbow Wave": {
        "id": AnimationId.RainbowWave.value,
        "description": "Rainbow wave moving across lights"
    },
    "Sparkle Glitter": {
        "id": AnimationId.SparkleGlitter.value,
        "description": "Random flashes (sparkles) across the LED strip"
    },
    "Bursting Sparkle": {
        "id": AnimationId.BurstingSparkle.value,
        "description": "Sparkle fire bursts across the LED strip."
    },
    "Fireworks": {
        "id": AnimationId.Fireworks.value,
        "description": "Group of \"fireworks\" bursting."
    }
}

# Map effects to their corresponding classes
effect_classes = {
    AnimationId.CycleFade.value: CycleFade,
    AnimationId.Fade.value: Fade,
    AnimationId.Blink.value: Blink,
    AnimationId.Chase.value: Chase,
    AnimationId.TwinkleStars.value: TwinkleStars,
    AnimationId.CandleFlicker.value: CandleFlicker,
    AnimationId.Bouncing.value: Bouncing,
    AnimationId.Twinkle.value: Twinkle,
    AnimationId.TwinkleCycle.value: TwinkleCycle,
    AnimationId.Cover.value: Cover,
    AnimationId.Cylon.value: Cylon,
    AnimationId.RainbowWave.value: RainbowWave,
    AnimationId.SparkleGlitter.value: SparkleGlitter,
    AnimationId.BurstingSparkle.value: BurstingSparkle,
    AnimationId.Fireworks.value: Fireworks,
}
