"""
Audioop compatibility module for Python 3.13+
This provides a minimal audioop implementation for discord.py compatibility
"""

import sys

# Check if we're on Python 3.13+ and audioop is missing
if sys.version_info >= (3, 13):
    try:
        import audioop
    except ImportError:
        # Create a minimal audioop module
        class AudioopCompat:
            @staticmethod
            def avg(*args, **kwargs):
                return b'\x00' * 1024  # Return silence
            
            @staticmethod
            def avgpp(*args, **kwargs):
                return b'\x00' * 1024
            
            @staticmethod
            def bias(*args, **kwargs):
                return args[0] if args else b'\x00' * 1024
            
            @staticmethod
            def cross(*args, **kwargs):
                return 0
            
            @staticmethod
            def findfactor(*args, **kwargs):
                return 1.0
            
            @staticmethod
            def findfit(*args, **kwargs):
                return 0
            
            @staticmethod
            def findmax(*args, **kwargs):
                return 0
            
            @staticmethod
            def getsample(*args, **kwargs):
                return 0
            
            @staticmethod
            def lin2adpcm(*args, **kwargs):
                return (b'\x00' * 1024, None)
            
            @staticmethod
            def lin2adpcm3(*args, **kwargs):
                return (b'\x00' * 1024, None)
            
            @staticmethod
            def lin2alaw(*args, **kwargs):
                return b'\x00' * 1024
            
            @staticmethod
            def lin2lin(*args, **kwargs):
                return args[0] if args else b'\x00' * 1024
            
            @staticmethod
            def lin2ulaw(*args, **kwargs):
                return b'\x00' * 1024
            
            @staticmethod
            def minmax(*args, **kwargs):
                return (0, 0)
            
            @staticmethod
            def mul(*args, **kwargs):
                return args[0] if args else b'\x00' * 1024
            
            @staticmethod
            def ratecv(*args, **kwargs):
                return (args[0] if args else b'\x00' * 1024, None)
            
            @staticmethod
            def reverse(*args, **kwargs):
                return args[0][::-1] if args else b'\x00' * 1024
            
            @staticmethod
            def rms(*args, **kwargs):
                return 0
            
            @staticmethod
            def tomono(*args, **kwargs):
                return args[0] if args else b'\x00' * 1024
            
            @staticmethod
            def tostereo(*args, **kwargs):
                return args[0] if args else b'\x00' * 1024
            
            @staticmethod
            def ulaw2lin(*args, **kwargs):
                return b'\x00' * 1024
        
        # Create the audioop module
        import types
        audioop = types.ModuleType('audioop')
        audioop.__file__ = __file__
        
        # Add all methods to the module
        for attr in dir(AudioopCompat):
            if not attr.startswith('_'):
                setattr(audioop, attr, getattr(AudioopCompat, attr))
        
        # Add to sys.modules so discord.py can import it
        sys.modules['audioop'] = audioop 