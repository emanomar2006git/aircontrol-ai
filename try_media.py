"""try_media.py
Manual test of MediaController on your real PC. No camera is used.
BEFORE you run it: open a video (YouTube, VLC, ...) and let it PLAY.
You have 8 seconds after starting to make sure the video is playing and visible.
Then the script sends: pause, pause again, play, play again. You only WATCH the video.
"""
import time

from commands.media_controller import MediaController

COUNTDOWN = 8
WAIT = 4  # seconds between the steps, so you can see what the video does


def step(number, text, sent, expected_sent, expected_video):
    ok = sent == expected_sent
    print(f"{number}) {text}")
    print(f"   key sent: {sent}   (expected {expected_sent})   -> [{'OK' if ok else 'FAIL'}]")
    print(f"   WATCH THE VIDEO: it should {expected_video}")
    return ok


def main():
    media = MediaController(min_interval=0.5)  # short cooldown only for this test
    print("Make sure a video is PLAYING now.")
    for left in range(COUNTDOWN, 0, -1):
        print(f"   starting in {left} ...")
        time.sleep(1)

    results = []
    results.append(step(1, "pause()", media.pause(), True, "PAUSE"))
    time.sleep(WAIT)
    results.append(step(2, "pause() again (must NOT press the key)", media.pause(), False, "stay paused"))
    time.sleep(WAIT)
    results.append(step(3, "play()", media.play(), True, "PLAY"))
    time.sleep(WAIT)
    results.append(step(4, "play() again (must NOT press the key)", media.play(), False, "keep playing"))

    if media.last_error:
        print(f"ERROR while sending the key: {media.last_error}")
    print()
    print("The key results are all OK." if all(results) else "SOMETHING FAILED - send this whole output to your mentor.")
    print("Now tell me what the VIDEO did in steps 1, 2, 3 and 4.")


if __name__ == "__main__":
    main()
