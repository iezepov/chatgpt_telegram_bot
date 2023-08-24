from typing import Optional, Any

import supabase
import uuid
from datetime import datetime
from supabase import create_client, Client

import config


class Database:
    def __init__(self):
        self.client: Client = create_client(config.supabase_url, config.supabase_key)

        self.users_table = self.client.table("users")
        self.dialogues_table = self.client.table("dialogues")

    def check_if_user_exists(self, user_id: int, raise_exception: bool = False):
        req = self.users_table.select("id").eq("id", user_id).execute()

        if req.data:
            return True
        else:
            if raise_exception:
                raise ValueError(f"User {user_id} does not exist")
            else:
                return False

    def add_new_user(
        self,
        user_id: int,
        chat_id: int,
        username: str = "",
        first_name: str = "",
        last_name: str = "",
    ):
        user_dict = {
            "id": user_id,
            "chat_id": chat_id,

            "username": username,
            "first_name": first_name,
            "last_name": last_name,

            "last_interaction": datetime.utcnow().isoformat(),
            "first_seen": datetime.utcnow().isoformat(),

            "current_dialog_id": None,
            "current_chat_mode": "assistant",
            "current_model": config.models["available_text_models"][0],

            "n_used_tokens": {},

            "n_generated_images": 0,
            "n_transcribed_seconds": 0.0  # voice message transcription
        }

        if not self.check_if_user_exists(user_id):
            self.users_table.insert(user_dict).execute()

    def start_new_dialog(self, user_id: int):
        self.check_if_user_exists(user_id, raise_exception=True)

        dialog_id = str(uuid.uuid4())
        dialog_dict = {
            "id": dialog_id,
            "user_id": user_id,
            "chat_mode": self.get_user_attribute(user_id, "current_chat_mode"),
            "start_time": datetime.utcnow().isoformat(),
            "model": self.get_user_attribute(user_id, "current_model"),
            "messages": []
        }
        print(dialog_dict)

        # add new dialog
        self.dialogues_table.insert(dialog_dict).execute()

        # update user's current dialog
        self.users_table.update({"current_dialog_id": dialog_id}).eq("id", user_id).execute()
        return dialog_id

    def get_user_attribute(self, user_id: int, key: str):
        self.check_if_user_exists(user_id, raise_exception=True)
        user_dict = self.users_table.select("*").eq("id", user_id).single().execute()
        return user_dict.data.get(key)

    def set_user_attribute(self, user_id: int, key: str, value: Any):
        self.check_if_user_exists(user_id, raise_exception=True)
        self.users_table.update({key: value}).eq("id", user_id).execute()

    def update_n_used_tokens(self, user_id: int, model: str, n_input_tokens: int, n_output_tokens: int):
        n_used_tokens_dict = self.get_user_attribute(user_id, "n_used_tokens")

        if model in n_used_tokens_dict:
            n_used_tokens_dict[model]["n_input_tokens"] += n_input_tokens
            n_used_tokens_dict[model]["n_output_tokens"] += n_output_tokens
        else:
            n_used_tokens_dict[model] = {
                "n_input_tokens": n_input_tokens,
                "n_output_tokens": n_output_tokens
            }

        self.set_user_attribute(user_id, "n_used_tokens", n_used_tokens_dict)

    def get_dialog_messages(self, user_id: int, dialog_id: Optional[str] = None):
        self.check_if_user_exists(user_id, raise_exception=True)

        if dialog_id is None:
            dialog_id = self.get_user_attribute(user_id, "current_dialog_id")

        dialog_dict = self.dialogues_table.select("messages").eq("id", dialog_id).single().execute()
        return dialog_dict.data["messages"]

    def set_dialog_messages(self, user_id: int, dialog_messages: list, dialog_id: Optional[str] = None):
        self.check_if_user_exists(user_id, raise_exception=True)

        if dialog_id is None:
            dialog_id = self.get_user_attribute(user_id, "current_dialog_id")

        self.dialogues_table.update({"messages": dialog_messages}).eq("id", dialog_id).execute()