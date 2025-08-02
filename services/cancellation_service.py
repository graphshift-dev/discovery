"""
GraphShift Cancellation Service - Handles clean shutdown and subprocess cleanup
Separates cancellation concerns from command orchestration
"""

import asyncio
import signal
import logging
import sys
from typing import Set, Optional

logger = logging.getLogger("graphshift.cancellation")


class CancellationService:
    """Service for handling clean cancellation and subprocess cleanup"""
    
    def __init__(self):
        self.active_processes: Set[asyncio.subprocess.Process] = set()
        self.cancellation_requested = False
        self.cleanup_in_progress = False
    
    def register_process(self, process: asyncio.subprocess.Process) -> None:
        """Register a subprocess for cleanup tracking"""
        self.active_processes.add(process)
    
    def unregister_process(self, process: asyncio.subprocess.Process) -> None:
        """Unregister a completed subprocess"""
        self.active_processes.discard(process)
    
    async def request_cancellation(self) -> None:
        """Request cancellation and start cleanup"""
        if self.cancellation_requested:
            return
            
        self.cancellation_requested = True
        print("\n[!] Analysis interrupted by user")
        print("[!] Operation cancelled by user")
        
        if self.active_processes:
            print("Exiting operation - cleanup may take a few seconds...")
            await self._cleanup_processes()
    
    async def _cleanup_processes(self) -> None:
        """Clean up all active subprocesses"""
        if self.cleanup_in_progress:
            return
            
        self.cleanup_in_progress = True
        
        try:
            # Terminate all active processes
            for process in list(self.active_processes):
                try:
                    if process.returncode is None:  # Still running
                        process.terminate()
                        
                        # Give process a chance to terminate gracefully
                        try:
                            await asyncio.wait_for(process.wait(), timeout=2.0)
                        except asyncio.TimeoutError:
                            # Force kill if it doesn't terminate
                            process.kill()
                            try:
                                await asyncio.wait_for(process.wait(), timeout=1.0)
                            except asyncio.TimeoutError:
                                pass  # Process might be already dead
                                
                except Exception as e:
                    # Suppress cleanup errors to avoid noise
                    logger.debug(f"Process cleanup error: {e}")
                finally:
                    self.unregister_process(process)
                    
        except Exception as e:
            logger.debug(f"Cleanup error: {e}")
        finally:
            self.cleanup_in_progress = False
    
    def is_cancelled(self) -> bool:
        """Check if cancellation has been requested"""
        return self.cancellation_requested
    
    async def check_cancellation(self) -> None:
        """Check for cancellation and raise if requested"""
        if self.cancellation_requested:
            raise asyncio.CancelledError("Operation cancelled by user")


# Global cancellation service instance
_cancellation_service: Optional[CancellationService] = None


def get_cancellation_service() -> CancellationService:
    """Get the global cancellation service instance"""
    global _cancellation_service
    if _cancellation_service is None:
        _cancellation_service = CancellationService()
    return _cancellation_service


async def handle_keyboard_interrupt() -> None:
    """Handle keyboard interrupt with clean cancellation"""
    print("\n[!] Analysis interrupted by user")
    print("[!] Operation cancelled by user")
    # Let the CancelledError propagate naturally to trigger subprocess cleanup 