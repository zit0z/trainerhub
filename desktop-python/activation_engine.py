from cheat_engine import CheatEngine

class ActivationEngine:
    def __init__(self):
        self.engine = CheatEngine()

    def activate(self, game_meta, trainer_data):
        """
        Main activation logic. 
        Checks if the trainer is a 'memory' type (AOB scan) or 'savegame' type.
        """
        method = trainer_data.get('method', 'memory')
        
        if method == 'memory':
            # Pattern scanning (The WeMod Way)
            pattern = trainer_data.get('pattern', '00 00 00') 
            offset = int(trainer_data.get('offset', 0))
            value = trainer_data.get('value', '0')
            
            # 1. Attach to process
            success, msg = self.engine.attach(game_meta['exe'])
            if not success: return False, msg
            
            # 2. Find pattern and write
            success, msg = self.engine.find_and_patch(pattern, offset, value)
            return success, msg if not success else f"Cheat active: {trainer_data['name']}"
            
        elif method == 'savegame':
            # Savegame edit
            path = game_meta['save_path'] # e.g. %APPDATA%/...
            # Find the actual save file (usually the most recent one in the folder)
            # Simple implementation for this demo:
            import os
            if not os.path.exists(os.path.expandvars(path)):
                return False, "Save folder not found"
            
            files = [os.path.join(os.path.expandvars(path), f) for f in os.listdir(os.path.expandvars(path))]
            if not files: return False, "No save files found"
            latest_save = max(files, key=os.path.getmtime)
            
            success, msg = self.engine.edit_savegame(latest_save, trainer_data['field'], trainer_data['value'])
            return success, msg
            
        return False, "Unknown activation method"
