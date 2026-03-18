#!/usr/bin/env python3
"""
Test Script for Interplanetary Network - Video/ML Version
==========================================================
Automated test script to verify all components are working correctly.
"""

import asyncio
import aiohttp
import time
import sys
import json
from typing import Dict, List, Tuple

# Test configuration
BASE_URLS = {
    "sender": "http://localhost:8001",
    "network": "http://localhost:8002",
    "edge": "http://localhost:8003",
    "client": "http://localhost:8004"
}

WS_URLS = {
    "sender": "ws://localhost:8001/stream",
    "network": "ws://localhost:8002/proxy",
    "edge": "ws://localhost:8003/process",
    "client": "ws://localhost:8004/stream"
}


class ComponentTester:
    """Test individual components."""
    
    def __init__(self, session: aiohttp.ClientSession):
        self.session = session
    
    async def test_health(self, name: str, url: str) -> Tuple[bool, str]:
        """Test health endpoint."""
        try:
            async with self.session.get(f"{url}/", timeout=5) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return True, f"✅ {name} health OK - {data.get('status', 'unknown')}"
                return False, f"❌ {name} health failed - HTTP {resp.status}"
        except Exception as e:
            return False, f"❌ {name} health error - {str(e)}"
    
    async def test_websocket(self, name: str, url: str, timeout: float = 5.0) -> Tuple[bool, str]:
        """Test WebSocket connection."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.ws_connect(url, timeout=timeout) as ws:
                    # Wait for first message
                    try:
                        msg = await asyncio.wait_for(ws.receive(), timeout=timeout)
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            return True, f"✅ {name} WebSocket OK - Received frame"
                        elif msg.type == aiohttp.WSMsgType.ERROR:
                            return False, f"❌ {name} WebSocket error"
                    except asyncio.TimeoutError:
                        return False, f"❌ {name} WebSocket timeout - no frames"
            return False, f"❌ {name} WebSocket connection failed"
        except Exception as e:
            return False, f"❌ {name} WebSocket error - {str(e)}"
    
    async def test_network_config(self) -> Tuple[bool, str]:
        """Test network simulator configuration."""
        try:
            # Get current config
            async with self.session.get(f"{BASE_URLS['network']}/config", timeout=5) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    delay = data.get('base_delay_ms', 'unknown')
                    return True, f"✅ Network config OK - Delay: {delay}ms"
            return False, "❌ Network config failed"
        except Exception as e:
            return False, f"❌ Network config error - {str(e)}"
    
    async def test_edge_ml(self) -> Tuple[bool, str]:
        """Test edge server ML capabilities."""
        try:
            async with self.session.get(f"{BASE_URLS['edge']}/config", timeout=5) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    ml_available = data.get('ml_available', False)
                    device = data.get('device', 'cpu')
                    if ml_available:
                        return True, f"✅ Edge ML OK - Using {device}"
                    else:
                        return True, f"⚠️ Edge ML not available - Using {device} (OpenCV fallback)"
            return False, "❌ Edge config failed"
        except Exception as e:
            return False, f"❌ Edge config error - {str(e)}"


async def run_tests():
    """Run all component tests."""
    print("=" * 60)
    print("🧪 Interplanetary Network - Component Tests")
    print("=" * 60)
    
    async with aiohttp.ClientSession() as session:
        tester = ComponentTester(session)
        results = []
        
        # Test 1: Health checks
        print("\n📋 Testing Health Endpoints...")
        for name, url in BASE_URLS.items():
            success, message = await tester.test_health(name.capitalize(), url)
            results.append((success, message))
            print(message)
        
        # Test 2: Network config
        print("\n📋 Testing Network Simulator...")
        success, message = await tester.test_network_config()
        results.append((success, message))
        print(message)
        
        # Test 3: Edge ML
        print("\n📋 Testing Edge Server ML...")
        success, message = await tester.test_edge_ml()
        results.append((success, message))
        print(message)
        
        # Test 4: WebSocket connections (quick test)
        print("\n📋 Testing WebSocket Connections...")
        
        # Test sender WebSocket
        success, message = await tester.test_websocket("Sender", WS_URLS["sender"], timeout=3.0)
        results.append((success, message))
        print(message)
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 Test Summary")
        print("=" * 60)
        
        passed = sum(1 for success, _ in results if success)
        total = len(results)
        
        print(f"Passed: {passed}/{total}")
        
        if passed == total:
            print("\n✅ All tests passed! System is ready.")
            print("\n👉 Next steps:")
            print("   1. Open http://localhost:8004 in your browser")
            print("   2. Click 'Start Comparison Demo'")
            print("   3. Adjust network delay using the dropdown")
            return 0
        else:
            print("\n❌ Some tests failed. Check the errors above.")
            print("\n👉 Troubleshooting:")
            print("   1. Make sure all components are running")
            print("   2. Check logs for each component")
            print("   3. Verify ports are not blocked by firewall")
            return 1


async def test_video_quality():
    """Test video quality metrics over time."""
    print("\n" + "=" * 60)
    print("🎥 Video Quality Test (30 seconds)")
    print("=" * 60)
    
    quality_samples = []
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.ws_connect(WS_URLS["client"], timeout=10) as ws:
                start_time = time.time()
                frame_count = 0
                synth_count = 0
                
                while time.time() - start_time < 30:
                    msg = await ws.receive()
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        data = json.loads(msg.data)
                        if data.get('type') == 'frame':
                            frame_count += 1
                            metadata = data.get('metadata', {})
                            
                            if metadata.get('is_synthesized'):
                                synth_count += 1
                                psnr = metadata.get('psnr', 0)
                                ssim = metadata.get('ssim', 0)
                                quality_samples.append({'psnr': psnr, 'ssim': ssim})
                    
                    # Progress indicator
                    if frame_count % 30 == 0:
                        elapsed = time.time() - start_time
                        print(f"\r⏱️  {elapsed:.0f}s | Frames: {frame_count} | Synth: {synth_count}", end="")
                
                print(f"\r✅ Test complete | Total: {frame_count} | Synthesized: {synth_count}")
                
                if quality_samples:
                    avg_psnr = sum(s['psnr'] for s in quality_samples) / len(quality_samples)
                    avg_ssim = sum(s['ssim'] for s in quality_samples) / len(quality_samples)
                    print(f"\n📊 Quality Metrics:")
                    print(f"   PSNR: {avg_psnr:.2f} dB (Good > 35)")
                    print(f"   SSIM: {avg_ssim:.4f} (Good > 0.95)")
                    
                    if avg_psnr > 35 and avg_ssim > 0.95:
                        print("✅ Quality is GOOD")
                    else:
                        print("⚠️ Quality could be improved")
                        
        except Exception as e:
            print(f"❌ Video quality test failed: {e}")


async def main():
    """Main test runner."""
    if len(sys.argv) > 1 and sys.argv[1] == "--quality":
        await test_video_quality()
    else:
        exit_code = await run_tests()
        if exit_code == 0:
            # Optionally run quality test
            if len(sys.argv) > 1 and sys.argv[1] == "--full":
                await test_video_quality()
        sys.exit(exit_code)


if __name__ == "__main__":
    asyncio.run(main())
