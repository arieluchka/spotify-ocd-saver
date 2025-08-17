from dataclasses import dataclass

@dataclass
class TriggerCategory:
    id: int
    trigger_category_name: str
    trigger_words: list[str]


class TriggersHandler:
    def __init__(self):
        ...

    def get_triggers_of_category(self) -> list[str]: #NOT SURE IF NEEDED
        ...

    def get_all_triggers_of_user(self, user_id: int) -> list[TriggerCategory]:
        """

        :param user_id:
        :return:
            {
                trigger_category_name: NAME,
            }
        """
        ...


    def add_a_new_category(self, user_id, category_name) -> int:
        """check category name is not already in db"""
        ...

    def delete_a_category(self, user_id, category_id) -> bool:
        """verify category has no triggers"""
        ...

    def put_triggers_to_category(self, user_id, category_id, triggers: list[str]):
        ...

    def remove_all_triggers_from_category(self, user_id, category_id):
        """"""
        self.put_triggers_to_category(user_id, category_id, [])