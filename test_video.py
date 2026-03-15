import asyncio
import websockets
import json
import base64

async def test_video():
    print("Testing video stream from sender...")
    try:
        async with websockets.connect("ws://localhost:8001/stream") as ws:
            print("Connected to sender!")
            
            for i in range(5):
                msg = await ws.recv()
                data = json.loads(msg)
                
                if data.get('type') == 'frame':
                    metadata = data.get('metadata', {})
                    frame_data = data.get('data', '')
                    
                    print(f"\nFrame {i+1}:")
                    print(f"  Frame ID: {metadata.get('frame_id', 'N/A')}")
                    print(f"  Size: {metadata.get('frame_size', 0)} bytes")
                    print(f"  Data length: {len(frame_data) if frame_data else 0} chars")
                    
                    if frame_data:
                        # Try to decode
                        try:
                            img_bytes = base64.b64decode(frame_data)
                            print(f"  Decoded: {len(img_bytes)} bytes - OK!")
                        except Exception as e:
                            print(f"  Decode error: {e}")
                else:
                    print(f"Unexpected message type: {data.get('type')}")
                    
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_video())
