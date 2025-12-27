# ai_editor_fixed.py
import re
import tkinter as tk
from tkinter import scrolledtext, messagebox
import subprocess
import tempfile
import os

class SimpleAIAnalyzer:
    def __init__(self):
        # Use raw strings to fix escape sequence warnings
        self.patterns = [
            # Performance patterns
            (r'for\s+i\s+in\s+range\s*\(\s*len\s*\(\s*(\w+)\s*\)\s*\)', 
             'Use enumerate() for index and value: for idx, item in enumerate(\\1)'),
            (r'(\w+)\s*=\s*\1\s*\+\s*(\w+)', 
             'Use augmented assignment: \\1 += \\2'),
            (r'if\s+(\w+)\s+in\s+\[', 
             'Use set for membership testing: if \\1 in {value1, value2}'),
            
            # Pythonic patterns
            (r'if\s+bool\s*\(\s*(\w+)\s*\)\s*==\s*True', 
             'Directly use: if \\1'),
            (r'if\s+len\s*\(\s*(\w+)\s*\)\s*>\s*0', 
             'Directly use: if \\1'),
            (r'if\s+(\w+)\s*==\s*False', 
             'Use: if not \\1'),
            
            # Security patterns
            (r'eval\s*\(', '⚠️ SECURITY: Avoid eval() - use ast.literal_eval() instead'),
            (r'exec\s*\(', '⚠️ SECURITY: Avoid exec() - potential security risk'),
            
            # Style patterns
            (r'except\s*:', 'Specify exception type: except ValueError:'),
            (r'print\s+"', 'Use print() function: print("text")'),
        ]
        
    def analyze_code(self, code):
        """Analyze code and return suggestions"""
        suggestions = []
        
        # Check patterns
        for pattern, advice in self.patterns:
            matches = re.finditer(pattern, code)
            for match in matches:
                line_num = code[:match.start()].count('\n') + 1
                
                # Create suggestion with context
                suggestion_text = f"Line {line_num}: {advice}"
                suggestions.append({
                    'line': line_num,
                    'suggestion': suggestion_text,
                    'category': self.get_category(pattern),
                    'priority': 'high' if '⚠️' in advice else 'medium'
                })
        
        # Additional checks
        lines = code.split('\n')
        for i, line in enumerate(lines, 1):
            # Check for TODO/FIXME
            if 'TODO' in line or 'FIXME' in line:
                suggestions.append({
                    'line': i,
                    'suggestion': f'Line {i}: Address TODO/FIXME comment',
                    'category': 'maintenance',
                    'priority': 'medium'
                })
            
            # Check for bare returns
            if line.strip() == 'return':
                suggestions.append({
                    'line': i,
                    'suggestion': f'Line {i}: Consider returning a specific value',
                    'category': 'style',
                    'priority': 'low'
                })
            
            # Check for print debugging
            if 'print(' in line and 'debug' not in line.lower():
                suggestions.append({
                    'line': i,
                    'suggestion': f'Line {i}: Consider using logging instead of print for debugging',
                    'category': 'best_practice',
                    'priority': 'low'
                })
        
        # Sort by line number
        suggestions.sort(key=lambda x: x['line'])
        return suggestions[:15]  # Return top 15
    
    def get_category(self, pattern):
        """Get category based on pattern"""
        if 'eval' in pattern or 'exec' in pattern:
            return 'security'
        elif 'for' in pattern or 'range' in pattern:
            return 'performance'
        elif 'if' in pattern or 'bool' in pattern:
            return 'pythonic'
        elif 'except' in pattern or 'print' in pattern:
            return 'style'
        else:
            return 'general'
    
    def get_code_metrics(self, code):
        """Get basic code metrics"""
        lines = code.split('\n')
        
        metrics = {
            'total_lines': len(lines),
            'code_lines': len([l for l in lines if l.strip() and not l.strip().startswith('#')]),
            'comment_lines': len([l for l in lines if l.strip().startswith('#')]),
            'functions': len(re.findall(r'def\s+\w+', code)),
            'classes': len(re.findall(r'class\s+\w+', code)),
            'complexity': self.calculate_complexity(code)
        }
        
        if metrics['total_lines'] > 0:
            metrics['comment_ratio'] = (metrics['comment_lines'] / metrics['total_lines']) * 100
        else:
            metrics['comment_ratio'] = 0
            
        return metrics
    
    def calculate_complexity(self, code):
        """Calculate simple complexity score"""
        score = 0
        lines = code.split('\n')
        
        for line in lines:
            # Skip comments
            if line.strip().startswith('#'):
                continue
                
            # Add points for control structures
            if any(keyword in line for keyword in ['if ', 'elif ', 'else:', 'for ', 'while ', 'try:', 'except ', 'and ', 'or ']):
                score += 1
            # Add points for nested structures
            if line.count('    ') > 2:  # Deep indentation
                score += 1
        
        return score

class AIPythonEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("🤖 AI Python Editor")
        self.root.geometry("1200x700")
        
        # Initialize AI analyzer
        self.ai_analyzer = SimpleAIAnalyzer()
        
        self.setup_ui()
        
    def setup_ui(self):
        # Main container
        main_container = tk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Left: Editor panel
        left_panel = tk.Frame(main_container)
        
        # Editor with line numbers
        editor_container = tk.Frame(left_panel)
        editor_container.pack(fill=tk.BOTH, expand=True)
        
        # Line numbers
        self.line_numbers = tk.Text(editor_container, width=4, padx=5,
                                   bg="#2D3748", fg="white", state='disabled',
                                   font=("Consolas", 11))
        self.line_numbers.pack(side=tk.LEFT, fill=tk.Y)
        
        # Main editor
        self.editor = scrolledtext.ScrolledText(editor_container,
                                               bg="#1E1F1C", fg="#F8F8F0",
                                               insertbackground="white",
                                               font=("Consolas", 12),
                                               undo=True)
        self.editor.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Add sample code
        self.insert_sample_code()
        
        # Bind events
        self.editor.bind("<KeyRelease>", self.on_editor_change)
        
        # Toolbar
        toolbar = tk.Frame(left_panel, bg="#2D3748", height=40)
        toolbar.pack(fill=tk.X, pady=(5, 0))
        
        # Toolbar buttons
        buttons = [
            ("▶ Run", self.run_code, "#48BB78"),
            ("🤖 Analyze", self.analyze_with_ai, "#9F7AEA"),
            ("💾 Save", self.save_file, "#4299E1"),
            ("📂 Open", self.open_file, "#ED8936"),
            ("🗑 Clear", self.clear_editor, "#F56565"),
        ]
        
        for text, command, color in buttons:
            btn = tk.Button(toolbar, text=text, command=command,
                           bg=color, fg="white", font=("Arial", 10, "bold"),
                           padx=15, pady=5)
            btn.pack(side=tk.LEFT, padx=5)
        
        main_container.add(left_panel)
        
        # Right: AI Panel
        right_panel = tk.Frame(main_container)
        
        # AI Recommendations
        ai_frame = tk.LabelFrame(right_panel, text="🧠 AI Suggestions",
                                font=("Arial", 12, "bold"))
        ai_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Recommendation list with scrollbar
        list_frame = tk.Frame(ai_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.recommendation_list = tk.Listbox(list_frame,
                                             yscrollcommand=scrollbar.set,
                                             bg="#2D3748",
                                             fg="white",
                                             font=("Arial", 10),
                                             selectbackground="#4FD1C7",
                                             height=15)
        self.recommendation_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.recommendation_list.yview)
        
        # Bind double-click
        self.recommendation_list.bind("<Double-Button-1>", self.show_suggestion_detail)
        
        # Action buttons
        action_frame = tk.Frame(ai_frame)
        action_frame.pack(fill=tk.X, padx=5, pady=5)
        
        tk.Button(action_frame, text="Apply to Line",
                 command=self.apply_suggestion,
                 bg="#38B2AC", fg="white").pack(side=tk.LEFT, padx=2)
        
        tk.Button(action_frame, text="Clear",
                 command=self.clear_suggestions,
                 bg="#F56565", fg="white").pack(side=tk.RIGHT, padx=2)
        
        # Auto-analyze toggle
        self.auto_analyze = tk.BooleanVar(value=True)
        tk.Checkbutton(action_frame, text="Auto-analyze",
                      variable=self.auto_analyze,
                      fg="white", bg="#2D3748").pack(side=tk.RIGHT, padx=10)
        
        # Code Metrics Panel
        metrics_frame = tk.LabelFrame(right_panel, text="📊 Code Metrics",
                                     font=("Arial", 12, "bold"))
        metrics_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.metrics_text = tk.Text(metrics_frame, height=8,
                                   bg="#2D3748", fg="white",
                                   font=("Consolas", 10))
        self.metrics_text.pack(fill=tk.BOTH, padx=5, pady=5)
        self.metrics_text.config(state='disabled')
        
        # Output Panel
        output_frame = tk.LabelFrame(right_panel, text="📤 Output",
                                    font=("Arial", 12, "bold"))
        output_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.output_text = scrolledtext.ScrolledText(output_frame,
                                                    bg="black", fg="#00FF00",
                                                    font=("Consolas", 10))
        self.output_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        main_container.add(right_panel)
        
        # Initial analysis
        self.update_line_numbers()
        self.analyze_with_ai()
        
    def insert_sample_code(self):
        """Insert sample code with common issues"""
        sample_code = '''# AI Python Editor - Sample Code
# Try analyzing this code with the AI button!

def calculate_sum(numbers):
    """Calculate sum of numbers"""
    result = 0
    for i in range(len(numbers)):
        result = result + numbers[i]  # Could use enumerate
    return result

def check_value(x):
    """Check if value is positive"""
    if bool(x > 0) == True:  # Redundant check
        return True
    else:
        return False

# TODO: Add more functionality here

# Main execution
data = [1, 2, 3, 4, 5]
print("Sum:", calculate_sum(data))

# Inefficient membership test
if 3 in [1, 2, 3, 4, 5]:  # Could use set
    print("Found")

# String concatenation in loop
output = ""
for i in range(5):
    output = output + str(i)  # Inefficient
print(output)'''
        
        self.editor.insert("1.0", sample_code)
    
    def on_editor_change(self, event=None):
        """Handle editor changes"""
        self.update_line_numbers()
        
        # Auto-analyze if enabled
        if self.auto_analyze.get():
            code = self.editor.get("1.0", tk.END)
            if len(code.strip()) > 10:  # Only if there's actual code
                self.root.after(1000, self.analyze_with_ai)  # Delay 1 second
    
    def update_line_numbers(self):
        """Update line numbers display"""
        lines = self.editor.get("1.0", tk.END).count("\n")
        
        self.line_numbers.config(state='normal')
        self.line_numbers.delete("1.0", tk.END)
        
        for i in range(1, lines + 1):
            self.line_numbers.insert(tk.END, f"{i}\n")
        
        self.line_numbers.config(state='disabled')
    
    def analyze_with_ai(self):
        """Analyze code with AI"""
        code = self.editor.get("1.0", tk.END)
        
        # Get AI suggestions
        suggestions = self.ai_analyzer.analyze_code(code)
        
        # Get metrics
        metrics = self.ai_analyzer.get_code_metrics(code)
        
        # Update UI
        self.update_suggestions_list(suggestions)
        self.update_metrics_display(metrics)
    
    def update_suggestions_list(self, suggestions):
        """Update the suggestions listbox"""
        self.recommendation_list.delete(0, tk.END)
        
        if not suggestions:
            self.recommendation_list.insert(0, "✅ No suggestions - code looks good!")
            return
        
        # Store suggestions data
        self.current_suggestions = suggestions
        
        for i, suggestion in enumerate(suggestions, 1):
            # Color code by priority
            emoji = {
                'high': '🔴',
                'medium': '🟡',
                'low': '🟢'
            }.get(suggestion['priority'], '⚪')
            
            # Truncate long text
            text = suggestion['suggestion']
            if len(text) > 60:
                text = text[:57] + "..."
            
            display_text = f"{emoji} {text}"
            self.recommendation_list.insert(tk.END, display_text)
            
            # Color the item
            color = {
                'high': '#F56565',
                'medium': '#ECC94B',
                'low': '#48BB78'
            }.get(suggestion['priority'], 'white')
            
            self.recommendation_list.itemconfig(tk.END, {'fg': color})
    
    def update_metrics_display(self, metrics):
        """Update metrics display"""
        self.metrics_text.config(state='normal')
        self.metrics_text.delete("1.0", tk.END)
        
        report = f"""📊 CODE ANALYSIS
{'='*30}

Lines: {metrics['total_lines']}
Code lines: {metrics['code_lines']}
Comment lines: {metrics['comment_lines']}
Comment ratio: {metrics['comment_ratio']:.1f}%
Functions: {metrics['functions']}
Classes: {metrics['classes']}
Complexity: {metrics['complexity']}

"""
        
        # Add quality assessment
        if metrics['comment_ratio'] < 10:
            report += "💡 Add more comments\n"
        if metrics['complexity'] > 10:
            report += "⚠️ High complexity\n"
        if metrics['functions'] == 0 and metrics['code_lines'] > 20:
            report += "💡 Consider adding functions\n"
        
        self.metrics_text.insert("1.0", report)
        self.metrics_text.config(state='disabled')
    
    def show_suggestion_detail(self, event):
        """Show detailed view of suggestion"""
        selection = self.recommendation_list.curselection()
        if not selection:
            return
        
        index = selection[0]
        if hasattr(self, 'current_suggestions') and index < len(self.current_suggestions):
            suggestion = self.current_suggestions[index]
            
            detail_window = tk.Toplevel(self.root)
            detail_window.title(f"Suggestion Details - Line {suggestion['line']}")
            detail_window.geometry("500x300")
            
            # Title
            title = tk.Label(detail_window, 
                            text=f"Line {suggestion['line']}: {suggestion['category'].upper()}",
                            font=("Arial", 12, "bold"))
            title.pack(pady=10)
            
            # Suggestion
            suggestion_text = tk.Text(detail_window, height=10, wrap=tk.WORD)
            suggestion_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            suggestion_text.insert("1.0", suggestion['suggestion'])
            suggestion_text.config(state='disabled')
            
            # Priority
            priority_label = tk.Label(detail_window,
                                     text=f"Priority: {suggestion['priority'].upper()}",
                                     font=("Arial", 10))
            priority_label.pack(pady=5)
            
            # Close button
            tk.Button(detail_window, text="Close",
                     command=detail_window.destroy).pack(pady=10)
    
    def apply_suggestion(self):
        """Apply selected suggestion to code"""
        selection = self.recommendation_list.curselection()
        if not selection:
            messagebox.showinfo("Info", "Select a suggestion first!")
            return
        
        index = selection[0]
        if hasattr(self, 'current_suggestions') and index < len(self.current_suggestions):
            suggestion = self.current_suggestions[index]
            line_num = suggestion['line']
            
            # Get the line
            code = self.editor.get("1.0", tk.END)
            lines = code.split('\n')
            
            if line_num <= len(lines):
                # Show current line
                current_line = lines[line_num - 1]
                messagebox.showinfo("Apply Suggestion",
                                  f"Line {line_num}:\n{current_line}\n\n"
                                  f"Suggestion: {suggestion['suggestion']}")
    
    def clear_suggestions(self):
        """Clear suggestions list"""
        self.recommendation_list.delete(0, tk.END)
        self.recommendation_list.insert(0, "Suggestions cleared")
    
    def run_code(self):
        """Execute Python code"""
        code = self.editor.get("1.0", tk.END)
        
        # Clear output
        self.output_text.delete("1.0", tk.END)
        self.output_text.insert(tk.END, "🚀 Running code...\n" + "="*50 + "\n\n")
        self.root.update()
        
        try:
            # Create temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(code)
                temp_file = f.name
            
            # Run the code
            result = subprocess.run(
                ["python", temp_file],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            # Display output
            if result.stdout:
                self.output_text.insert(tk.END, "📤 OUTPUT:\n")
                self.output_text.insert(tk.END, result.stdout)
                self.output_text.insert(tk.END, "\n")
            
            if result.stderr:
                self.output_text.insert(tk.END, "❌ ERRORS:\n")
                self.output_text.insert(tk.END, result.stderr)
                self.output_text.insert(tk.END, "\n")
            
            self.output_text.insert(tk.END, "="*50 + "\n")
            
            if result.returncode == 0:
                self.output_text.insert(tk.END, "✅ Execution successful!\n")
            else:
                self.output_text.insert(tk.END, f"⚠️ Exit code: {result.returncode}\n")
                
        except subprocess.TimeoutExpired:
            self.output_text.insert(tk.END, "⏰ Timeout: Code took too long to execute\n")
        except Exception as e:
            self.output_text.insert(tk.END, f"❌ Error: {str(e)}\n")
        finally:
            try:
                os.unlink(temp_file)
            except:
                pass
    
    def save_file(self):
        """Save current code to file"""
        from tkinter import filedialog
        
        filepath = filedialog.asksaveasfilename(
            defaultextension=".py",
            filetypes=[("Python files", "*.py"), ("All files", "*.*")]
        )
        
        if filepath:
            with open(filepath, 'w') as f:
                f.write(self.editor.get("1.0", tk.END))
            
            messagebox.showinfo("Saved", f"File saved:\n{filepath}")
            self.root.title(f"AI Python Editor - {os.path.basename(filepath)}")
    
    def open_file(self):
        """Open Python file"""
        from tkinter import filedialog
        
        filepath = filedialog.askopenfilename(
            filetypes=[("Python files", "*.py"), ("All files", "*.*")]
        )
        
        if filepath:
            with open(filepath, 'r') as f:
                self.editor.delete("1.0", tk.END)
                self.editor.insert("1.0", f.read())
            
            self.update_line_numbers()
            self.root.title(f"AI Python Editor - {os.path.basename(filepath)}")
    
    def clear_editor(self):
        """Clear editor content"""
        if messagebox.askyesno("Clear", "Clear all code?"):
            self.editor.delete("1.0", tk.END)
            self.output_text.delete("1.0", tk.END)
            self.update_line_numbers()
            self.clear_suggestions()
            self.metrics_text.config(state='normal')
            self.metrics_text.delete("1.0", tk.END)
            self.metrics_text.config(state='disabled')

def main():
    root = tk.Tk()
    editor = AIPythonEditor(root)
    root.mainloop()

if __name__ == "__main__":
    main()