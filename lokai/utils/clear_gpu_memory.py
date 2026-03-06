"""
Utility script to forcefully clear GPU memory.
Can be run standalone if GPU memory is stuck after closing the application.
"""
import sys
import gc


def clear_gpu_memory():
    """Clear GPU memory."""
    try:
        import torch

        if not torch.cuda.is_available():
            print("CUDA not available. No GPU memory to clear.")
            return False

        print("Clearing GPU memory...")

        gc.collect()

        device_count = torch.cuda.device_count()

        for device_id in range(device_count):
            try:
                torch.cuda.synchronize(device_id)
                torch.cuda.empty_cache()

                try:
                    torch.cuda.reset_peak_memory_stats(device_id)
                except Exception:
                    pass

                try:
                    torch.cuda.ipc_collect()
                except AttributeError:
                    pass

                print(f"GPU {device_id} memory cleared")
            except Exception as e:
                print(f"Error clearing GPU {device_id}: {e}")

        gc.collect()

        try:
            for device_id in range(device_count):
                allocated = torch.cuda.memory_allocated(device_id) / 1024**3
                reserved = torch.cuda.memory_reserved(device_id) / 1024**3
                print(f"GPU {device_id}: {allocated:.2f} GB allocated, {reserved:.2f} GB reserved")
        except Exception:
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
