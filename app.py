import asyncio
import os
import requests
from livekit import rtc

VOCAL_BRIDGE_API_KEY = os.environ.get('VOCAL_BRIDGE_API_KEY')
VOCAL_BRIDGE_URL = 'https://vocalbridgeai.com'


def get_voice_token(participant_name: str = 'Python Client'):
    """Get a voice token from Vocal Bridge API."""
    response = requests.post(
        f'{VOCAL_BRIDGE_URL}/api/v1/token',
        headers={
            'X-API-Key': VOCAL_BRIDGE_API_KEY,
            'Content-Type': 'application/json'
        },
        json={'participant_name': participant_name}
    )
    response.raise_for_status()
    return response.json()


async def main():
    # Get token
    token_data = get_voice_token()
    print(f"Connecting to room: {token_data['room_name']}")

    # Create room
    room = rtc.Room()

    # Set up event handlers
    @room.on("track_subscribed")
    def on_track_subscribed(track, publication, participant):
        if track.kind == rtc.TrackKind.KIND_AUDIO:
            print("Agent audio connected!")
            # Process audio stream
            audio_stream = rtc.AudioStream(track)
            # ... handle audio frames

    @room.on("disconnected")
    def on_disconnected():
        print("Disconnected from room")

    # Connect
    await room.connect(token_data['livekit_url'], token_data['token'])
    print(f"Connected! Room: {room.name}")

    # Publish microphone (requires audio input device)
    source = rtc.AudioSource(sample_rate=48000, num_channels=1)
    track = rtc.LocalAudioTrack.create_audio_track("microphone", source)
    await room.local_participant.publish_track(track)
    print("Microphone enabled - start speaking!")

    # Keep running
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        await room.disconnect()


if __name__ == '__main__':
    asyncio.run(main())