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
        today_btn.setMaximumWidth(80)
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
        sort_layout = QFormLayout(sort_group)

        self.sort_combo = ComboBox()
        self.sort_combo.addItems(["Create Date", "Priority", "Due Date", "Name"])
        self.sort_combo.currentTextChanged.connect(self.sort_todos)

        self.sort_order_combo = ComboBox()
        self.sort_order_combo.addItems(["Ascending", "Descending"])
        self.sort_order_combo.currentTextChanged.connect(self.sort_todos)

        sort_row_layout = QHBoxLayout()
        sort_row_layout.addWidget(self.sort_combo)
        sort_row_layout.addWidget(self.sort_order_combo)
        # sort_order_combo 宽度小些
        self.sort_order_combo.setMaximumWidth(120)
        sort_layout.addRow("Sort by:", sort_row_layout)
        # sort_layout.addStretch()

        # sort_layout.addStretch()
        self.main_layout.addWidget(sort_group)
        
        # Todo tree (for nested items)
        self.todo_tree = TreeWidget()
        self.todo_tree.setHeaderLabels(["Task", "Priority", "Due Date", "Created", "Actions"])
        self.todo_tree.setColumnWidth(0, 800)  # Increased width for checkbox and text
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
        self.resize(600, 300)
        
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
        today_btn.setMaximumWidth(80)
        due_date_layout.addWidget(today_btn)
        
        tomorrow_btn = PushButton("TOM")
        # tomorrow_btn.setIcon(Icon(FluentIcon.TRAIN))
        tomorrow_btn.setToolTip("Tomorrow")
        tomorrow_btn.clicked.connect(lambda: self.due_date_edit.setDate(QDate.currentDate().addDays(1)))
        tomorrow_btn.setMaximumWidth(80)
        due_date_layout.addWidget(tomorrow_btn)
        
        week_btn = PushButton("WEEK")
        # week_btn.setIcon(Icon(FluentIcon.DATE_TIME))
        week_btn.setToolTip("Next Week")
        week_btn.clicked.connect(lambda: self.due_date_edit.setDate(QDate.currentDate().addDays(7)))
        week_btn.setMaximumWidth(80)
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


class JiraInterface(QWidget):
    """Jira User Story生成器界面"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        
        # 标题
        title_label = BodyLabel("Jira User Story Generator")
        title_label.setStyleSheet("font-size: 24px; font-weight: bold; margin-bottom: 20px;")
        self.main_layout.addWidget(title_label)
        
        # 输入区域
        input_group = QGroupBox("Generate User Stories")
        input_layout = QFormLayout(input_group)
        
        # 用户输入框
        self.user_input = LineEdit()
        self.user_input.setPlaceholderText("Enter your requirement or feature description...")
        self.user_input.returnPressed.connect(self.generate_user_stories)
        input_layout.addRow("Requirement:", self.user_input)
        
        # 生成和创建按钮行
        buttons_layout = QHBoxLayout()
        
        self.generate_button = PrimaryPushButton("Generate User Stories")
        self.generate_button.setIcon(Icon(FluentIcon.ROBOT))
        self.generate_button.clicked.connect(self.generate_user_stories)
        buttons_layout.addWidget(self.generate_button)
        
        self.create_all_button = PrimaryPushButton("Create All in Jira")
        self.create_all_button.setIcon(Icon(FluentIcon.ADD))
        self.create_all_button.clicked.connect(self.create_all_stories_in_jira)
        self.create_all_button.setEnabled(False)
        buttons_layout.addWidget(self.create_all_button)
        
        self.create_selected_button = PushButton("Create Selected")
        self.create_selected_button.setIcon(Icon(FluentIcon.ADD))
        self.create_selected_button.clicked.connect(self.create_selected_story_in_jira)
        self.create_selected_button.setEnabled(False)
        buttons_layout.addWidget(self.create_selected_button)
        
        input_layout.addRow(buttons_layout)
        
        self.main_layout.addWidget(input_group)
        
        # 结果显示区域
        results_group = QGroupBox("Generated User Stories")
        results_layout = QVBoxLayout(results_group)
        
        # 使用TreeWidget显示生成的User Stories
        self.stories_tree = TreeWidget()
        self.stories_tree.setHeaderLabels(["Title", "Type", "Priority"])
        self.stories_tree.setColumnWidth(0, 400)
        self.stories_tree.setColumnWidth(1, 100)
        self.stories_tree.setColumnWidth(2, 100)
        self.stories_tree.setMinimumHeight(200)  # 设置最小高度
        self.stories_tree.setMaximumHeight(300)  # 设置最大高度
        self.stories_tree.setStyleSheet("""
            QTreeWidget::item { 
                height: 35px; 
                padding: 5px;
                border-bottom: 1px solid #e0e0e0;
            }
            QTreeWidget::item:selected {
                background-color: #e3f2fd;
            }
            QTreeWidget::item:hover {
                background-color: #f5f5f5;
            }
        """)
        self.stories_tree.itemClicked.connect(self.on_story_selected)
        results_layout.addWidget(self.stories_tree)
        
        self.main_layout.addWidget(results_group)
        
        # 详细信息显示区域
        details_group = QGroupBox("Story Details & Edit")
        details_layout = QVBoxLayout(details_group)
        details_layout.setSpacing(15)  # 增加垂直间距
        
        # 创建滚动区域
        from PyQt6.QtWidgets import QScrollArea
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        # scroll_area.setMinimumHeight(300)
        # scroll_area.setMaximumHeight(800)
        
        # 创建滚动内容容器
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(20)  # 增加组件间距
        scroll_layout.setContentsMargins(10, 10, 10, 10)
        
        # 编辑表单
        edit_form = QFormLayout()
        edit_form.setVerticalSpacing(15)  # 增加表单行间距
        
        # 标题编辑
        self.title_edit = LineEdit()
        self.title_edit.setPlaceholderText("Story title...")
        self.title_edit.setMinimumHeight(35)
        edit_form.addRow("Title:", self.title_edit)
        
        # 类型选择
        self.type_combo = ComboBox()
        self.type_combo.addItems(["Story", "Task", "Epic", "Bug"])
        self.type_combo.setMinimumHeight(35)
        edit_form.addRow("Type:", self.type_combo)
        
        # 优先级选择
        self.priority_combo = ComboBox()
        self.priority_combo.addItems(["Low", "Medium", "High", "Critical"])
        self.priority_combo.setMinimumHeight(35)
        edit_form.addRow("Priority:", self.priority_combo)
        
        scroll_layout.addLayout(edit_form)
        
        # 描述编辑
        desc_label = BodyLabel("Description:")
        desc_label.setStyleSheet("font-weight: bold; margin-top: 10px; margin-bottom: 5px;")
        scroll_layout.addWidget(desc_label)
        
        from PyQt6.QtWidgets import QTextEdit
        self.description_edit = QTextEdit()
        self.description_edit.setPlaceholderText("Enter story description...")
        self.description_edit.setMinimumHeight(100)
        self.description_edit.setMaximumHeight(150)
        self.description_edit.setStyleSheet("""
            QTextEdit {
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                padding: 8px;
                font-size: 14px;
                line-height: 1;
            }
            QTextEdit:focus {
                border-color: #0078d4;
            }
        """)
        scroll_layout.addWidget(self.description_edit)
        
        # 验收标准编辑
        criteria_label = BodyLabel("Acceptance Criteria:")
        criteria_label.setStyleSheet("font-weight: bold; margin-top: 15px; margin-bottom: 5px;")
        scroll_layout.addWidget(criteria_label)
        
        self.criteria_edit = QTextEdit()
        self.criteria_edit.setPlaceholderText("Enter acceptance criteria (one per line)...")
        self.criteria_edit.setMinimumHeight(100)
        self.criteria_edit.setMaximumHeight(150)
        self.criteria_edit.setStyleSheet("""
            QTextEdit {
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                padding: 8px;
                font-size: 14px;
                line-height: 1;
            }
            QTextEdit:focus {
                border-color: #0078d4;
            }
        """)
        scroll_layout.addWidget(self.criteria_edit)
        
        # 编辑按钮
        edit_buttons_layout = QHBoxLayout()
        edit_buttons_layout.setSpacing(10)
        edit_buttons_layout.setContentsMargins(0, 15, 0, 0)
        
        self.update_story_button = PushButton("Update Story")
        self.update_story_button.setIcon(Icon(FluentIcon.EDIT))
        self.update_story_button.clicked.connect(self.update_selected_story)
        self.update_story_button.setEnabled(False)
        self.update_story_button.setMinimumHeight(35)
        edit_buttons_layout.addWidget(self.update_story_button)
        
        self.delete_story_button = PushButton("Delete Story")
        self.delete_story_button.setIcon(Icon(FluentIcon.DELETE))
        self.delete_story_button.clicked.connect(self.delete_selected_story)
        self.delete_story_button.setEnabled(False)
        self.delete_story_button.setMinimumHeight(35)
        edit_buttons_layout.addWidget(self.delete_story_button)
        
        edit_buttons_layout.addStretch()
        scroll_layout.addLayout(edit_buttons_layout)
        
        # 设置滚动内容
        scroll_area.setWidget(scroll_content)
        details_layout.addWidget(scroll_area)
        
        self.main_layout.addWidget(details_group)
        
        # 存储当前选中的故事
        self.current_selected_item = None

    def generate_user_stories(self):
        """生成用户故事"""
        user_input = self.user_input.text().strip()
        if not user_input:
            InfoBar.warning(
                title='Warning',
                content='Please enter a requirement description',
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP_RIGHT,
                duration=2000,
                parent=self.window()
            )
            return
        
        # 显示生成中状态
        self.generate_button.setEnabled(False)
        
        # 使用Dummy数据模拟大模型生成
        stories = self.generate_dummy_stories(user_input)
        
        # 清空之前的结果
        self.stories_tree.clear()
        self.clear_edit_form()
        
        # 填充生成的故事
        for story in stories:
            item = QTreeWidgetItem(self.stories_tree)
            item.setText(0, story["title"])
            item.setText(1, story["type"])
            item.setText(2, story["priority"])
            
            # 存储完整的故事数据
            item.setData(0, Qt.ItemDataRole.UserRole, story)
        
        # 展开所有项目
        self.stories_tree.expandAll()
        
        # 更新状态
        self.generate_button.setEnabled(True)
        self.create_all_button.setEnabled(True)
        
        InfoBar.success(
            title='Success',
            content=f'Generated {len(stories)} user stories',
            orient=Qt.Orientation.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP_RIGHT,
            duration=2000,
            parent=self.window()
        )

    def generate_dummy_stories(self, user_input):
        """生成虚拟的用户故事数据"""
        import random
        
        # 基于用户输入生成相关的故事
        base_stories = [
            {
                "title": f"As a user, I want to {user_input.lower()}",
                "type": "Story",
                "priority": "High",
                "description": f"As a user, I want to {user_input.lower()} so that I can achieve my goals efficiently.\n\nThis feature will enable users to perform the requested functionality with ease and reliability.",
                "acceptance_criteria": [
                    f"Given that I am a logged-in user",
                    f"When I attempt to {user_input.lower()}",
                    f"Then the system should allow me to complete the action successfully",
                    f"And I should receive appropriate feedback",
                    f"And the action should be logged for audit purposes"
                ],
                "acceptance_criteria_en": [
                    f"Given that I am a logged-in user",
                    f"When I attempt to {user_input.lower()}",
                    f"Then the system should allow me to complete the action successfully",
                    f"And I should receive appropriate feedback",
                    f"And the action should be logged for audit purposes"
                ]
            },
            {
                "title": f"As an admin, I want to manage {user_input.lower()} settings",
                "type": "Story", 
                "priority": "Medium",
                "description": f"As an administrator, I need to be able to configure and manage settings related to {user_input.lower()}.\n\nThis will ensure proper governance and control over the feature.",
                "acceptance_criteria": [
                    f"Given that I am an administrator",
                    f"When I access the admin panel",
                    f"Then I should see options to configure {user_input.lower()} settings",
                    f"And I should be able to save changes",
                    f"And changes should take effect immediately"
                ],
                "acceptance_criteria_en": [
                    f"Given that I am an administrator",
                    f"When I access the admin panel",
                    f"Then I should see options to configure {user_input.lower()} settings",
                    f"And I should be able to save changes",
                    f"And changes should take effect immediately"
                ]
            },
            {
                "title": f"As a developer, I want to implement {user_input.lower()} API",
                "type": "Task",
                "priority": "High", 
                "description": f"Implement the backend API endpoints required to support {user_input.lower()} functionality.\n\nThis includes creating the necessary controllers, services, and data models.",
                "acceptance_criteria": [
                    f"Given the API specification",
                    f"When I implement the {user_input.lower()} endpoints",
                    f"Then all endpoints should return proper HTTP status codes",
                    f"And response data should match the specification",
                    f"And proper error handling should be implemented"
                ],
                "acceptance_criteria_en": [
                    f"Given the API specification",
                    f"When I implement the {user_input.lower()} endpoints",
                    f"Then all endpoints should return proper HTTP status codes",
                    f"And response data should match the specification",
                    f"And proper error handling should be implemented"
                ]
            }
        ]
        
        # 随机选择1-3个故事
        num_stories = random.randint(1, 3)
        selected_stories = random.sample(base_stories, min(num_stories, len(base_stories)))
        
        return selected_stories

    def on_story_selected(self, item, column):
        """当选择一个故事时加载到编辑表单"""
        story_data = item.data(0, Qt.ItemDataRole.UserRole)
        if story_data:
            self.current_selected_item = item
            
            # 填充编辑表单
            self.title_edit.setText(story_data['title'])
            
            # 设置类型
            type_index = self.type_combo.findText(story_data['type'])
            if type_index >= 0:
                self.type_combo.setCurrentIndex(type_index)
            
            # 设置优先级
            priority_index = self.priority_combo.findText(story_data['priority'])
            if priority_index >= 0:
                self.priority_combo.setCurrentIndex(priority_index)
            
            # 设置描述
            self.description_edit.setPlainText(story_data['description'])
            
            # 设置验收标准
            criteria_text = '\n'.join(story_data['acceptance_criteria'])
            self.criteria_edit.setPlainText(criteria_text)
            
            # 启用编辑按钮
            self.update_story_button.setEnabled(True)
            self.delete_story_button.setEnabled(True)
            self.create_selected_button.setEnabled(True)

    def update_selected_story(self):
        """更新选中的故事"""
        if not self.current_selected_item:
            return
        
        # 获取编辑后的数据
        updated_story = {
            'title': self.title_edit.text().strip(),
            'type': self.type_combo.currentText(),
            'priority': self.priority_combo.currentText(),
            'description': self.description_edit.toPlainText().strip(),
            'acceptance_criteria': [line.strip() for line in self.criteria_edit.toPlainText().split('\n') if line.strip()]
        }
        
        # 验证数据
        if not updated_story['title']:
            InfoBar.warning(
                title='Warning',
                content='Title cannot be empty',
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP_RIGHT,
                duration=2000,
                parent=self.window()
            )
            return
        
        # 更新树形控件显示
        self.current_selected_item.setText(0, updated_story['title'])
        self.current_selected_item.setText(1, updated_story['type'])
        self.current_selected_item.setText(2, updated_story['priority'])
        
        # 更新存储的数据
        self.current_selected_item.setData(0, Qt.ItemDataRole.UserRole, updated_story)
        
        InfoBar.success(
            title='Success',
            content='Story updated successfully',
            orient=Qt.Orientation.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP_RIGHT,
            duration=2000,
            parent=self.window()
        )

    def delete_selected_story(self):
        """删除选中的故事"""
        if not self.current_selected_item:
            return
        
        # 确认删除
        from qfluentwidgets import MessageBox
        w = MessageBox(
            'Delete Story',
            'Are you sure you want to delete this story?',
            self.window()
        )
        if w.exec():
            # 从树形控件中移除
            root = self.stories_tree.invisibleRootItem()
            root.removeChild(self.current_selected_item)
            
            # 清空编辑表单
            self.clear_edit_form()
            self.current_selected_item = None
            
            # 更新按钮状态
            self.update_story_button.setEnabled(False)
            self.delete_story_button.setEnabled(False)
            self.create_selected_button.setEnabled(False)
            
            # 检查是否还有故事
            if self.stories_tree.topLevelItemCount() == 0:
                self.create_all_button.setEnabled(False)
            
            InfoBar.success(
                title='Success',
                content='Story deleted successfully',
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP_RIGHT,
                duration=2000,
                parent=self.window()
            )

    def clear_edit_form(self):
        """清空编辑表单"""
        self.title_edit.clear()
        self.type_combo.setCurrentIndex(0)
        self.priority_combo.setCurrentIndex(1)  # Medium
        self.description_edit.clear()
        self.criteria_edit.clear()
        
        # 重置按钮状态
        self.update_story_button.setEnabled(False)
        self.delete_story_button.setEnabled(False)
        self.create_selected_button.setEnabled(False)
        self.current_selected_item = None

    def create_selected_story_in_jira(self):
        """在Jira中创建选中的故事"""
        if not self.current_selected_item:
            return
        
        # 从环境变量读取项目键
        project_key = os.getenv('JIRA_PROJECT_KEY', '').strip()
        if not project_key:
            InfoBar.warning(
                title='Warning',
                content='JIRA_PROJECT_KEY environment variable not set',
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP_RIGHT,
                duration=2000,
                parent=self.window()
            )
            return
        
        story_data = self.current_selected_item.data(0, Qt.ItemDataRole.UserRole)
        self.create_story_in_jira(story_data, project_key)

    def create_all_stories_in_jira(self):
        """在Jira中创建所有故事"""
        # 从环境变量读取项目键
        project_key = os.getenv('JIRA_PROJECT_KEY', '').strip()
        if not project_key:
            InfoBar.warning(
                title='Warning',
                content='JIRA_PROJECT_KEY environment variable not set',
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP_RIGHT,
                duration=2000,
                parent=self.window()
            )
            return
        
        # 获取所有故事
        stories = []
        for i in range(self.stories_tree.topLevelItemCount()):
            item = self.stories_tree.topLevelItem(i)
            story_data = item.data(0, Qt.ItemDataRole.UserRole)
            if story_data:
                stories.append(story_data)
        
        if not stories:
            InfoBar.warning(
                title='Warning',
                content='No stories to create',
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP_RIGHT,
                duration=2000,
                parent=self.window()
            )
            return
        
        # 创建所有故事
        success_count = 0
        for story in stories:
            if self.create_story_in_jira(story, project_key, show_individual_notification=False):
                success_count += 1
        
        InfoBar.success(
            title='Success',
            content=f'Created {success_count}/{len(stories)} stories in Jira',
            orient=Qt.Orientation.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP_RIGHT,
            duration=3000,
            parent=self.window()
        )

    def create_story_in_jira(self, story_data, project_key, show_individual_notification=True):
        """在Jira中创建单个故事 (使用Dummy数据模拟)"""
        try:
            # 模拟API调用延迟
            import time
            time.sleep(0.5)
            
            # 模拟Jira API调用
            # 这里应该是真实的Jira API调用
            jira_issue = {
                'key': f'{project_key}-{hash(story_data["title"]) % 1000:03d}',
                'summary': story_data['title'],
                'description': story_data['description'],
                'issuetype': story_data['type'],
                'priority': story_data['priority'],
                'acceptance_criteria': story_data['acceptance_criteria']
            }
            
            # 模拟成功创建
            if show_individual_notification:
                InfoBar.success(
                    title='Jira Story Created',
                    content=f'Created: {jira_issue["key"]} - {story_data["title"][:50]}...',
                    orient=Qt.Orientation.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP_RIGHT,
                    duration=3000,
                    parent=self.window()
                )
            
            return True
            
        except Exception as e:
            if show_individual_notification:
                InfoBar.error(
                    title='Error',
                    content=f'Failed to create story in Jira: {str(e)}',
                    orient=Qt.Orientation.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP_RIGHT,
                    duration=3000,
                    parent=self.window()
                )
            return False


class TodoApp(FluentWindow):
    def __init__(self):
        super().__init__()
        self.todo_interface = TodoInterface()
        self.button_interface = JiraInterface()
        self.init_ui()
        self.setup_window()

    def init_ui(self):
        # Set object name before adding the interface
        self.todo_interface.setObjectName("todoInterface")
        self.button_interface.setObjectName("JiraInterface")
        
        # Add the todo interface to the FluentWindow
        self.addSubInterface(self.todo_interface, Icon(FluentIcon.HOME), "Todo List", NavigationItemPosition.TOP)
        
        # Add the button interface to the FluentWindow
        self.addSubInterface(self.button_interface, Icon(FluentIcon.ROBOT), "Story Generator", NavigationItemPosition.TOP)

    def setup_window(self):
        """Setup window properties - center and maximize"""
        self.setWindowTitle("Fluent Todo List")
        
        # Set initial size
        self.resize(1200, 800)
        
        # Center the window on screen
        from PyQt6.QtWidgets import QApplication
        screen = QApplication.primaryScreen()
        if screen:
            screen_geometry = screen.availableGeometry()
            window_geometry = self.frameGeometry()
            center_point = screen_geometry.center()
            window_geometry.moveCenter(center_point)
            self.move(window_geometry.topLeft())
        
        # Maximize the window
        self.showMaximized()


def main():
    app = QApplication(sys.argv)
    # Set dark theme
    setTheme(Theme.LIGHT)
    
    window = TodoApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()