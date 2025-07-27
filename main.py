import sys
import json
import os
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
    QTreeWidgetItem,
    QFormLayout, QGroupBox, QDialog, QDialogButtonBox
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QTextCharFormat
from qfluentwidgets import (
    FluentWindow, PrimaryPushButton, PushButton, LineEdit, 
    MessageBox, Theme, setTheme, Icon,
    BodyLabel, InfoBar, InfoBarPosition, NavigationItemPosition,
    FluentIcon, TreeWidget, ComboBox, DateEdit, CheckBox
)


class TodoInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.todo_file = "todos.json"
        self.todos = []  # Will store hierarchical todo structure
        # Store references to custom widgets for tree items
        self.item_widgets = {}  # item_id -> {'checkbox': CheckBox, 'text_label': BodyLabel}
        self.init_ui()
        self.load_todos()

    def init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        # # title_label = SubtitleLabel("Todo List")
        # title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # self.main_layout.addWidget(title_label)
        
        # Input area
        input_group = QGroupBox("Add New Todo")
        input_form = QFormLayout(input_group)
        
        # Todo text input
        self.todo_input = LineEdit()
        self.todo_input.setPlaceholderText("Enter a new todo item...")
        self.todo_input.returnPressed.connect(self.add_todo)
        input_form.addRow("Task:", self.todo_input)
        
        # Priority selection
        self.priority_combo = ComboBox()
        self.priority_combo.addItems(["Low", "Medium", "High", "Critical"])
        self.priority_combo.setCurrentIndex(1)  # Default to Medium
        input_form.addRow("Priority:", self.priority_combo)
        
        # Due date selection with enhanced calendar popup
        due_date_layout = QHBoxLayout()
        self.due_date_edit = DateEdit()
        self.due_date_edit.setDate(QDate.currentDate().addDays(7))  # Default to 1 week from now
        self.due_date_edit.setCalendarPopup(True)
        self.due_date_edit.setDisplayFormat("yyyy-MM-dd")  # Show day of week
        self.due_date_edit.setMinimumWidth(200)
        
        # Configure calendar widget for better UX
        calendar = self.due_date_edit.calendarWidget()
        if calendar:
            calendar.setGridVisible(True)
            calendar.setFirstDayOfWeek(Qt.DayOfWeek.Monday)
            # Highlight today with special formatting
            today_format = QTextCharFormat()
            today_format.setBackground(self.palette().color(self.palette().ColorRole.Highlight))
            today_format.setForeground(self.palette().color(self.palette().ColorRole.HighlightedText))
            calendar.setDateTextFormat(QDate.currentDate(), today_format)
        
        due_date_layout.addWidget(self.due_date_edit)
        
        # Add quick date buttons
        today_btn = PushButton("TDY")
        today_btn.clicked.connect(lambda: self.due_date_edit.setDate(QDate.currentDate()))
        today_btn.setMaximumWidth(60)
        due_date_layout.addWidget(today_btn)
        
        tomorrow_btn = PushButton("TOM")
        tomorrow_btn.clicked.connect(lambda: self.due_date_edit.setDate(QDate.currentDate().addDays(1)))
        tomorrow_btn.setMaximumWidth(80)
        due_date_layout.addWidget(tomorrow_btn)
        
        week_btn = PushButton("WEEK")
        week_btn.clicked.connect(lambda: self.due_date_edit.setDate(QDate.currentDate().addDays(7)))
        week_btn.setMaximumWidth(80)
        due_date_layout.addWidget(week_btn)
        
        input_form.addRow("Due Date:", due_date_layout)
        
        # Add button and Clear button in the same row
        button_layout = QHBoxLayout()
        self.add_button = PrimaryPushButton("Add Todo")
        self.add_button.clicked.connect(self.add_todo)
        button_layout.addWidget(self.add_button)
        
        # Add Clear Completed button next to Add Todo
        self.clear_button = PushButton("Clear Completed")
        self.clear_button.clicked.connect(self.clear_completed)
        button_layout.addWidget(self.clear_button)
        
        # button_layout.addStretch()  # Push buttons to the left
        input_form.addRow(button_layout)
        
        self.main_layout.addWidget(input_group)
        
        # Sorting controls
        sort_group = QGroupBox("Sort Options")
        sort_layout = QHBoxLayout(sort_group)
        
        sort_layout.addWidget(BodyLabel("Sort by:"))
        self.sort_combo = ComboBox()
        self.sort_combo.addItems(["Create Date", "Priority", "Due Date", "Name"])
        self.sort_combo.currentTextChanged.connect(self.sort_todos)
        sort_layout.addWidget(self.sort_combo)
        
        self.sort_order_combo = ComboBox()
        self.sort_order_combo.addItems(["Ascending", "Descending"])
        self.sort_order_combo.currentTextChanged.connect(self.sort_todos)
        sort_layout.addWidget(self.sort_order_combo)
        
        # sort_layout.addStretch()
        self.main_layout.addWidget(sort_group)
        
        # Todo tree (for nested items)
        self.todo_tree = TreeWidget()
        self.todo_tree.setHeaderLabels(["Task", "Priority", "Due Date", "Created", "Actions"])
        self.todo_tree.setColumnWidth(0, 400)  # Increased width for checkbox and text
        self.todo_tree.setColumnWidth(1, 80)
        self.todo_tree.setColumnWidth(2, 100)
        self.todo_tree.setColumnWidth(3, 100)
        self.todo_tree.setColumnWidth(4, 180)  # Increased width for action buttons
        # Set uniform row height for better button display
        self.todo_tree.setUniformRowHeights(True)
        # Set indentation to provide space for expand icons
        self.todo_tree.setIndentation(30)  # Increase indentation for better spacing
        # Increase row height for better visual appearance
        self.todo_tree.setStyleSheet("QTreeWidget::item { height: 50px; }")
        # Temporarily disconnect signal during tree population
        self.todo_tree.itemChanged.connect(self.update_todo_status)
        self.main_layout.addWidget(self.todo_tree)
        
        
        # Status bar
        self.status_label = BodyLabel("Total: 0 | Completed: 0")
        self.main_layout.addWidget(self.status_label)

    def add_todo(self):
        text = self.todo_input.text().strip()
        if text:
            priority = self.priority_combo.currentText()
            due_date = self.due_date_edit.date().toString("yyyy-MM-dd")
            create_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            todo = {
                "text": text,
                "completed": False,
                "priority": priority,
                "due_date": due_date,
                "create_date": create_date,
                "children": []
            }
            self.todos.append(todo)
            self.sort_todos()  # Sort after adding
            self.todo_input.clear()
            # Reset to defaults
            self.priority_combo.setCurrentIndex(1)  # Medium
            self.due_date_edit.setDate(QDate.currentDate().addDays(7))
            self.update_status()
            # Auto-save after adding todo
            self.save_todos(show_notification=False)
            InfoBar.success(
                title='Success',
                content=f'Added: {text}',
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP_RIGHT,
                duration=2000,
                parent=self.window()
            )
        else:
            InfoBar.warning(
                title='Warning',
                content='Please enter a todo item',
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP_RIGHT,
                duration=2000,
                parent=self.window()
            )

    def add_sub_todo_to_item(self, parent_todo, parent_item):
        """Add sub-item to a specific parent item using dialog"""
        dialog = TodoEditDialog({}, self, is_new=True)
        dialog.setWindowTitle("Add Sub-item")
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Get the new sub-todo data
            new_data = dialog.get_updated_data()
            new_data["create_date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            new_data["completed"] = False
            new_data["children"] = []
            
            parent_todo["children"].append(new_data)
            self.sort_todos()  # Sort after adding
            self.update_status()
            # Auto-save after adding sub-todo
            self.save_todos(show_notification=False)
            InfoBar.success(
                title='Success',
                content=f'Added sub-item: {new_data["text"]}',
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP_RIGHT,
                duration=2000,
                parent=self.window()
            )

    def find_todo_by_item(self, item):
        """Find the todo data structure corresponding to a tree widget item"""
        def search_todos(todos, target_item, current_item=None):
            for todo in todos:
                if current_item is None:
                    # This is a root level search
                    root_items = [self.todo_tree.topLevelItem(i) for i in range(self.todo_tree.topLevelItemCount())]
                    for i, root_item in enumerate(root_items):
                        if root_item == target_item:
                            return self.todos[i]
                        result = search_in_children(self.todos[i]["children"], target_item, root_item)
                        if result:
                            return result
                else:
                    if current_item == target_item:
                        return todo
                    result = search_in_children(todo["children"], target_item, current_item)
                    if result:
                        return result
            return None
            
        def search_in_children(children, target_item, parent_item):
            for i, child_todo in enumerate(children):
                child_item = parent_item.child(i)
                if child_item == target_item:
                    return child_todo
                result = search_in_children(child_todo["children"], target_item, child_item)
                if result:
                    return result
            return None
            
        return search_todos(self.todos, item)

    def remove_todo_item(self, todo_data, tree_item):
        """Remove a specific todo item"""
        text = todo_data["text"]
        self.remove_todo_from_data(tree_item)
        self.update_todo_tree()
        self.update_status()
        # Auto-save after removing todo
        self.save_todos(show_notification=False)
        InfoBar.success(
            title='Success',
            content=f'Removed: {text}',
            orient=Qt.Orientation.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP_RIGHT,
            duration=2000,
            parent=self.window()
        )

    def remove_todo_from_data(self, item):
        """Remove a todo item from the data structure"""
        def remove_from_list(todos, target_item, parent_item=None):
            if parent_item is None:
                # Check root level
                root_items = [self.todo_tree.topLevelItem(i) for i in range(self.todo_tree.topLevelItemCount())]
                for i, root_item in enumerate(root_items):
                    if root_item == target_item:
                        del self.todos[i]
                        return True
                    if remove_from_children(self.todos[i]["children"], target_item, root_item):
                        return True
            return False
            
        def remove_from_children(children, target_item, parent_item):
            for i, child_todo in enumerate(children):
                child_item = parent_item.child(i)
                if child_item == target_item:
                    del children[i]
                    return True
                if remove_from_children(child_todo["children"], target_item, child_item):
                    return True
            return False
            
        remove_from_list(self.todos, item)

    def on_fluent_checkbox_clicked(self, checked, todo_data, tree_item):
        """Handle qfluentwidgets CheckBox click events"""
        todo_data["completed"] = checked
        
        # Apply visual style to the current item
        self.apply_completed_style(tree_item, checked)
        
        # Mark all children with the same completion status as parent
        self.mark_children_completed(todo_data, checked)
        # Update the tree display to reflect the changes
        self.update_tree_item_children(tree_item, checked)
        
        self.update_status()
        # Auto-save after status change
        self.save_todos(show_notification=False)

    def update_todo_status(self, item, column):
        # This method is kept for backward compatibility but may not be used with fluent checkboxes
        if column == 0:  # Only handle checkbox changes in the first column
            todo_data = self.find_todo_by_item(item)
            if todo_data:
                is_completed = item.checkState(0) == Qt.CheckState.Checked
                todo_data["completed"] = is_completed
                
                # Apply visual style to the current item
                self.apply_completed_style(item, is_completed)
                
                # Mark all children with the same completion status as parent
                self.mark_children_completed(todo_data, is_completed)
                # Update the tree display to reflect the changes
                self.update_tree_item_children(item, is_completed)
                
                self.update_status()
                # Auto-save after status change
                self.save_todos(show_notification=False)

    def mark_children_completed(self, todo_data, completed_status):
        """Recursively mark all children as completed or uncompleted"""
        for child in todo_data["children"]:
            child["completed"] = completed_status
            # Recursively mark grandchildren
            self.mark_children_completed(child, completed_status)

    def update_tree_item_children(self, tree_item, completed_status):
        """Recursively update the visual state of all child tree items"""
        # Update all children of this tree item
        for i in range(tree_item.childCount()):
            child_item = tree_item.child(i)
            
            # Update fluent checkbox if it exists
            child_item_id = id(child_item)
            if child_item_id in self.item_widgets and self.item_widgets[child_item_id]['checkbox']:
                self.item_widgets[child_item_id]['checkbox'].setChecked(completed_status)
            else:
                # Fallback to traditional checkbox
                check_state = Qt.CheckState.Checked if completed_status else Qt.CheckState.Unchecked
                child_item.setCheckState(0, check_state)
            
            # Apply visual style to child items
            self.apply_completed_style(child_item, completed_status)
            # Recursively update grandchildren
            self.update_tree_item_children(child_item, completed_status)

    def clear_completed(self):
        completed_count = self.count_completed_root_todos(self.todos)
        if completed_count > 0:
            self.todos = self.remove_completed_root_todos(self.todos)
            self.update_todo_tree()
            self.update_status()
            # Auto-save after clearing completed
            self.save_todos(show_notification=False)
            InfoBar.success(
                title='Success',
                content=f'Cleared {completed_count} completed root items',
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP_RIGHT,
                duration=2000,
                parent=self.window()
            )
        else:
            InfoBar.warning(
                title='Warning',
                content='No completed root items to clear',
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP_RIGHT,
                duration=2000,
                parent=self.window()
            )

    def count_completed_todos(self, todos):
        """Recursively count completed todos"""
        count = 0
        for todo in todos:
            if todo["completed"]:
                count += 1
            count += self.count_completed_todos(todo["children"])
        return count

    def count_completed_root_todos(self, todos):
        """Count only completed root-level todos (not sub-items)"""
        count = 0
        for todo in todos:
            if todo["completed"]:
                count += 1
        return count

    def remove_completed_root_todos(self, todos):
        """Remove only completed root-level todos, preserve sub-items"""
        filtered_todos = []
        for todo in todos:
            if not todo["completed"]:
                filtered_todos.append(todo)
        return filtered_todos

    def remove_completed_todos(self, todos):
        """Recursively remove completed todos (kept for other uses)"""
        filtered_todos = []
        for todo in todos:
            if not todo["completed"]:
                todo["children"] = self.remove_completed_todos(todo["children"])
                filtered_todos.append(todo)
        return filtered_todos

    def clear_all_todos(self):
        if len(self.todos) > 0:
            w = MessageBox(
                'Clear All Todos',
                'Are you sure you want to clear all todos?',
                self.window()
            )
            if w.exec():
                self.todos.clear()
                self.update_todo_tree()
                self.update_status()
                # Auto-save after clearing all
                self.save_todos(show_notification=False)
                InfoBar.success(
                    title='Success',
                    content='Cleared all todos',
                    orient=Qt.Orientation.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP_RIGHT,
                    duration=2000,
                    parent=self.window()
                )
        else:
            InfoBar.warning(
                title='Warning',
                content='No todos to clear',
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP_RIGHT,
                duration=2000,
                parent=self.window()
            )

    def update_todo_tree(self):
        # Temporarily disconnect the signal to prevent unwanted updates during population
        try:
            self.todo_tree.itemChanged.disconnect(self.update_todo_status)
        except TypeError:
            # Signal was not connected, ignore the error
            pass
        
        # Clear widget references to avoid memory leaks
        self.item_widgets.clear()
        
        self.todo_tree.clear()
        self.populate_tree_items(self.todos, None)
        self.todo_tree.expandAll()
        # Reconnect the signal after population is complete
        self.todo_tree.itemChanged.connect(self.update_todo_status)

    def populate_tree_items(self, todos, parent_item):
        """Recursively populate tree widget items"""
        for todo in todos:
            if parent_item is None:
                item = QTreeWidgetItem(self.todo_tree)
            else:
                item = QTreeWidgetItem(parent_item)
            
            # Set text and additional info
            item.setText(0, todo["text"])
            item.setText(1, todo.get("priority", "Medium"))
            # Format due date display to match create date format (yyyy-MM-dd)
            due_date = todo.get("due_date", "")
            if due_date:
                try:
                    date_obj = QDate.fromString(due_date, "yyyy-MM-dd")
                    if date_obj.isValid():
                        # Format as yyyy-MM-dd to match create date format
                        formatted_date = date_obj.toString("yyyy-MM-dd")
                        item.setText(2, formatted_date)
                    else:
                        item.setText(2, due_date)
                except Exception:
                    item.setText(2, due_date)
            else:
                item.setText(2, "")
            item.setText(3, todo.get("create_date", "")[:10] if todo.get("create_date") else "")  # Show only date part
            
            # Create a custom checkbox widget with text using qfluentwidgets
            checkbox_widget = QWidget()
            checkbox_layout = QHBoxLayout(checkbox_widget)
            
            # Simple left margin to avoid overlap with expand icon
            # The tree indentation will handle the hierarchical spacing
            checkbox_layout.setContentsMargins(20, 0, 0, 0)
            
            fluent_checkbox = CheckBox()
            fluent_checkbox.setChecked(todo["completed"])
            fluent_checkbox.clicked.connect(lambda checked, t=todo, i=item: self.on_fluent_checkbox_clicked(checked, t, i))
            checkbox_layout.addWidget(fluent_checkbox)
            
            # Add text label next to checkbox
            text_label = BodyLabel(todo["text"])
            text_label.setWordWrap(True)
            checkbox_layout.addWidget(text_label)
            checkbox_layout.addStretch()
            
            # Store references for later access using item's memory address as key
            item_id = id(item)
            self.item_widgets[item_id] = {
                'checkbox': fluent_checkbox,
                'text_label': text_label
            }
            
            # Clear the item text since we're using custom widget
            item.setText(0, "")
            
            # Set the checkbox widget in the first column
            self.todo_tree.setItemWidget(item, 0, checkbox_widget)
            
            # Apply completed style
            self.apply_completed_style(item, todo["completed"])
            
            # Color code by priority
            self.apply_priority_style(item, todo.get("priority", "Medium"))
            
            # Add action buttons in the Actions column
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(2, 2, 2, 2)
            actions_layout.setSpacing(2)
            
            # Edit button
            edit_button = PushButton("Edit")
            edit_button.setMaximumWidth(50)
            # edit_button.setMaximumHeight(35)
            edit_button.clicked.connect(lambda checked, t=todo, i=item: self.edit_todo_item(t, i))
            actions_layout.addWidget(edit_button)
            
            # Add sub-item button
            add_sub_button = PushButton("Sub")
            add_sub_button.setMaximumWidth(50)
            # add_sub_button.setMaximumHeight(35)
            add_sub_button.clicked.connect(lambda checked, t=todo, i=item: self.add_sub_todo_to_item(t, i))
            actions_layout.addWidget(add_sub_button)
            
            # Remove button
            remove_button = PushButton("Del")
            remove_button.setMaximumWidth(50)
            # remove_button.setMaximumHeight(35)
            remove_button.clicked.connect(lambda checked, t=todo, i=item: self.remove_todo_item(t, i))
            actions_layout.addWidget(remove_button)
            
            self.todo_tree.setItemWidget(item, 4, actions_widget)
            
            # Recursively add children
            if todo["children"]:
                self.populate_tree_items(todo["children"], item)

    def edit_todo_item(self, todo_data, tree_item):
        """Open edit dialog for a todo item"""
        dialog = TodoEditDialog(todo_data, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Update the todo data with new values
            updated_data = dialog.get_updated_data()
            todo_data.update(updated_data)
            
            # Refresh the tree display
            self.sort_todos()  # This will refresh and sort
            self.update_status()
            # Auto-save after editing
            self.save_todos(show_notification=False)
            
            InfoBar.success(
                title='Success',
                content=f'Updated: {updated_data["text"]}',
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP_RIGHT,
                duration=2000,
                parent=self.window()
            )

    def apply_completed_style(self, item, is_completed):
        """Apply or remove strikethrough style for completed items"""
        # Style the custom text label in the checkbox widget
        item_id = id(item)
        if item_id in self.item_widgets and self.item_widgets[item_id]['text_label']:
            text_label = self.item_widgets[item_id]['text_label']
            font = text_label.font()
            if is_completed:
                # Add strikethrough for completed items
                font.setStrikeOut(True)
                text_label.setFont(font)
                # Make text slightly grayed out
                text_label.setStyleSheet("color: gray;")
            else:
                # Remove strikethrough for uncompleted items
                font.setStrikeOut(False)
                text_label.setFont(font)
                # Restore normal text color
                text_label.setStyleSheet("")
        
        # Style other columns (Priority, Due Date, Created)
        for col in range(1, 4):  # Style columns 1-3 (Priority, Due Date, Created)
            font = item.font(col)
            if is_completed:
                # Add strikethrough for completed items
                font.setStrikeOut(True)
                # Make text slightly grayed out
                item.setForeground(col, self.palette().color(self.palette().ColorRole.PlaceholderText))
            else:
                # Remove strikethrough for uncompleted items
                font.setStrikeOut(False)
                # Restore normal text color
                item.setForeground(col, self.palette().color(self.palette().ColorRole.Text))
            item.setFont(col, font)

    def apply_priority_style(self, item, priority):
        """Apply color coding based on priority"""
        from PyQt6.QtGui import QColor
        
        priority_colors = {
            "Critical": QColor(255, 100, 100),  # Red
            "High": QColor(255, 165, 0),        # Orange
            "Medium": QColor(100, 149, 237),    # Blue
            "Low": QColor(144, 238, 144)        # Light Green
        }
        
        color = priority_colors.get(priority, priority_colors["Medium"])
        item.setForeground(1, color)  # Color the priority column

    def sort_todos(self):
        """Sort todos based on selected criteria"""
        sort_by = self.sort_combo.currentText()
        ascending = self.sort_order_combo.currentText() == "Ascending"
        
        def get_sort_key(todo):
            if sort_by == "Create Date":
                return todo.get("create_date", "")
            elif sort_by == "Priority":
                priority_order = {"Critical": 4, "High": 3, "Medium": 2, "Low": 1}
                return priority_order.get(todo.get("priority", "Medium"), 2)
            elif sort_by == "Due Date":
                return todo.get("due_date", "9999-12-31")  # Put items without due date at end
            elif sort_by == "Name":
                return todo.get("text", "").lower()
            return ""
        
        def sort_recursive(todos_list):
            # Sort current level
            todos_list.sort(key=get_sort_key, reverse=not ascending)
            # Recursively sort children
            for todo in todos_list:
                if todo["children"]:
                    sort_recursive(todo["children"])
        
        sort_recursive(self.todos)
        self.update_todo_tree()
        # Auto-save after sorting
        self.save_todos(show_notification=False)

    def update_status(self):
        total = self.count_total_todos(self.todos)
        completed = self.count_completed_todos(self.todos)
        self.status_label.setText(f"Total: {total} | Completed: {completed}")

    def count_total_todos(self, todos):
        """Recursively count total todos"""
        count = len(todos)
        for todo in todos:
            count += self.count_total_todos(todo["children"])
        return count

    def save_todos(self, show_notification=False):
        try:
            with open(self.todo_file, 'w', encoding='utf-8') as f:
                json.dump(self.todos, f, indent=2, ensure_ascii=False)
            if show_notification:
                InfoBar.success(
                    title='Success',
                    content='Todos saved successfully',
                    orient=Qt.Orientation.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP_RIGHT,
                    duration=2000,
                    parent=self.window()
                )
        except Exception as e:
            print(f"Save error: {e}")  # Debug print
            MessageBox("Error", f"Failed to save todos: {str(e)}", self.window()).exec()

    def load_todos(self):
        if os.path.exists(self.todo_file):
            try:
                with open(self.todo_file, 'r', encoding='utf-8') as f:
                    loaded_todos = json.load(f)
                
                # Ensure backward compatibility - add children field if missing
                self.todos = self.ensure_children_field(loaded_todos)
                
                self.update_todo_tree()
                self.update_status()
            except Exception as e:
                print(f"Load error: {e}")  # Debug print
                MessageBox("Error", f"Failed to load todos: {str(e)}", self.window()).exec()
        else:
            # Create empty file if it doesn't exist
            self.save_todos()

    def ensure_children_field(self, todos):
        """Ensure all todo items have required fields for backward compatibility"""
        for todo in todos:
            if "children" not in todo:
                todo["children"] = []
            # Ensure completed field exists and preserve its value
            if "completed" not in todo:
                todo["completed"] = False
            # Ensure new fields exist with defaults
            if "priority" not in todo:
                todo["priority"] = "Medium"
            if "due_date" not in todo:
                todo["due_date"] = ""
            if "create_date" not in todo:
                todo["create_date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            # Recursively process children
            if todo["children"]:
                todo["children"] = self.ensure_children_field(todo["children"])
        return todos


class TodoEditDialog(QDialog):
    def __init__(self, todo_data, parent=None, is_new=False):
        super().__init__(parent)
        self.todo_data = todo_data.copy()  # Work with a copy
        self.is_new = is_new
        self.init_ui()
        self.populate_fields()
        
    def init_ui(self):
        self.setWindowTitle("Edit Todo Item")
        self.setModal(True)
        self.resize(400, 300)
        
        layout = QVBoxLayout(self)
        
        # Create form
        form_layout = QFormLayout()
        
        # Task text
        self.text_edit = LineEdit()
        self.text_edit.setPlaceholderText("Enter task description...")
        form_layout.addRow("Task:", self.text_edit)
        
        # Priority
        self.priority_combo = ComboBox()
        self.priority_combo.addItems(["Low", "Medium", "High", "Critical"])
        form_layout.addRow("Priority:", self.priority_combo)
        
        # Due date with quick buttons
        due_date_layout = QHBoxLayout()
        self.due_date_edit = DateEdit()
        self.due_date_edit.setCalendarPopup(True)
        self.due_date_edit.setDisplayFormat("yyyy-MM-dd")
        self.due_date_edit.setMinimumWidth(200)        
        due_date_layout.addWidget(self.due_date_edit)
        
        # Quick date buttons with icons
        today_btn = PushButton("TDY")
        # today_btn.setIcon(Icon(FluentIcon.CALENDAR))
        today_btn.setToolTip("Today")
        today_btn.clicked.connect(lambda: self.due_date_edit.setDate(QDate.currentDate()))
        today_btn.setMaximumWidth(40)
        due_date_layout.addWidget(today_btn)
        
        tomorrow_btn = PushButton("TOM")
        # tomorrow_btn.setIcon(Icon(FluentIcon.TRAIN))
        tomorrow_btn.setToolTip("Tomorrow")
        tomorrow_btn.clicked.connect(lambda: self.due_date_edit.setDate(QDate.currentDate().addDays(1)))
        tomorrow_btn.setMaximumWidth(40)
        due_date_layout.addWidget(tomorrow_btn)
        
        week_btn = PushButton("WEEK")
        # week_btn.setIcon(Icon(FluentIcon.DATE_TIME))
        week_btn.setToolTip("Next Week")
        week_btn.clicked.connect(lambda: self.due_date_edit.setDate(QDate.currentDate().addDays(7)))
        week_btn.setMaximumWidth(40)
        due_date_layout.addWidget(week_btn)
        
        form_layout.addRow("Due Date:", due_date_layout)
        
        layout.addLayout(form_layout)
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
    def populate_fields(self):
        """Populate form fields with current todo data"""
        self.text_edit.setText(self.todo_data.get("text", ""))
        
        priority = self.todo_data.get("priority", "Medium")
        priority_index = ["Low", "Medium", "High", "Critical"].index(priority)
        self.priority_combo.setCurrentIndex(priority_index)
        
        due_date_str = self.todo_data.get("due_date", "")
        if due_date_str:
            due_date = QDate.fromString(due_date_str, "yyyy-MM-dd")
            if due_date.isValid():
                self.due_date_edit.setDate(due_date)
            else:
                self.due_date_edit.setDate(QDate.currentDate())
        else:
            self.due_date_edit.setDate(QDate.currentDate())
            
    def get_updated_data(self):
        """Return updated todo data"""
        return {
            "text": self.text_edit.text().strip(),
            "priority": self.priority_combo.currentText(),
            "due_date": self.due_date_edit.date().toString("yyyy-MM-dd"),
            "completed": self.todo_data.get("completed", False),  # Preserve completion status
            "create_date": self.todo_data.get("create_date", ""),  # Preserve creation date
            "children": self.todo_data.get("children", [])  # Preserve children
        }


class TodoApp(FluentWindow):
    def __init__(self):
        super().__init__()
        self.todo_interface = TodoInterface()
        self.init_ui()
        self.resize(900, 600)
        self.setWindowTitle("Fluent Todo List")

    def init_ui(self):
        # Set object name before adding the interface
        self.todo_interface.setObjectName("todoInterface")
        # Add the todo interface to the FluentWindow
        self.addSubInterface(self.todo_interface, Icon(FluentIcon.HOME), "Todo List", NavigationItemPosition.TOP)


def main():
    app = QApplication(sys.argv)
    # Set dark theme
    setTheme(Theme.LIGHT)
    
    window = TodoApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()