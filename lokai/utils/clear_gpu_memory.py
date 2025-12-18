"""
Utility script to forcefully clear GPU memory.
Can be run standalone if GPU memory is stuck after closing the application.
"""
import sys
import gc

def clear_gpu_memory():
    """Aggressively clear GPU memory."""
    try:
        import torch
        
        if not torch.cuda.is_available():
            print("CUDA not available. No GPU memory to clear.")
            return False
        
        print("Clearing GPU memory...")
        
        # Force garbage collection multiple times
        for _ in range(5):
            gc.collect()
        
        # Get all devices
        device_count = torch.cuda.device_count()
        
        for device_id in range(device_count):
            try:
                device = torch.device(f"cuda:{device_id}")
                
                # Synchronize
                torch.cuda.synchronize(device_id)
                
                # Clear cache multiple times
                for _ in range(10):
                    torch.cuda.empty_cache()
                
                # Reset peak memory stats
                try:
                    torch.cuda.reset_peak_memory_stats(device_id)
                except:
                    pass
                
                # Collect IPC resources
                try:
                    torch.cuda.ipc_collect()
                except AttributeError:
                    pass
                
                print(f"GPU {device_id} memory cleared")
            except Exception as e:
                print(f"Error clearing GPU {device_id}: {e}")
        
        # Final garbage collection
        for _ in range(5):
            gc.collect()
        
        # Print memory info
        try:
            for device_id in range(device_count):
                allocated = torch.cuda.memory_allocated(device_id) / 1024**3
                reserved = torch.cuda.memory_reserved(device_id) / 1024**3
                print(f"GPU {device_id}: {allocated:.2f} GB allocated, {reserved:.2f} GB reserved")
        except:
            pass
        
        print("GPU memory clearing complete!")
        return True
        
    except ImportError:
        print("PyTorch not installed. Cannot clear GPU memory.")
        return False
    except Exception as e:
        print(f"Error clearing GPU memory: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("=" * 50)
    print("GPU Memory Cleaner")
    print("=" * 50)
    success = clear_gpu_memory()
    sys.exit(0 if success else 1)

