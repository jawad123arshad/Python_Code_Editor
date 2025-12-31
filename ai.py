# ai_editor_with_ml.py
import re
import tkinter as tk
from tkinter import scrolledtext, messagebox
import subprocess
import tempfile
import os
import numpy as np
import pickle
from collections import Counter
from datetime import datetime

# ========================================================
# ML MODEL IMPLEMENTATIONS
# ========================================================

class MLCodeAnalyzer:
    """Machine Learning-based code analyzer"""
    
    def __init__(self):
        self.pattern_model = self.load_or_create_model()
        self.code_features = {}
        self.learning_rate = 0.1
        
    def load_or_create_model(self):
        """Load existing model or create new one"""
        model_file = "code_patterns_model.pkl"
        
        if os.path.exists(model_file):
            try:
                with open(model_file, 'rb') as f:
                    return pickle.load(f)
            except:
                pass
        
        # Initialize with basic patterns
        base_patterns = {
            'performance': {
                'range_len_pattern': {'weight': 0.9, 'count': 0},
                'inefficient_concatenation': {'weight': 0.8, 'count': 0},
                'list_membership': {'weight': 0.7, 'count': 0}
            },
            'style': {
                'redundant_bool': {'weight': 0.6, 'count': 0},
                'bare_except': {'weight': 0.8, 'count': 0},
                'print_debugging': {'weight': 0.5, 'count': 0}
            },
            'security': {
                'eval_usage': {'weight': 0.95, 'count': 0},
                'exec_usage': {'weight': 0.9, 'count': 0}
            }
        }
        return base_patterns
    
    def save_model(self):
        """Save trained model to file"""
        with open("code_patterns_model.pkl", 'wb') as f:
            pickle.dump(self.pattern_model, f)
    
    def extract_features(self, code):
        """Extract features from code for ML analysis"""
        features = {}
        
        # Basic metrics
        lines = code.split('\n')
        features['line_count'] = len(lines)
        features['indentation_depth'] = self.calculate_avg_indentation(code)
        features['function_count'] = len(re.findall(r'def\s+\w+', code))
        features['class_count'] = len(re.findall(r'class\s+\w+', code))
        
        # Complexity metrics - FIXED: Added this method
        features['complexity_score'] = self.calculate_complexity(code)
        features['nesting_depth'] = self.calculate_max_nesting(code)
        
        # Pattern frequencies
        pattern_counts = self.count_patterns(code)
        for category, patterns in pattern_counts.items():
            for pattern, count in patterns.items():
                features[f'{category}_{pattern}'] = count
        
        return features
    
    # ADDED THIS MISSING METHOD
    def calculate_complexity(self, code):
        """Calculate code complexity score"""
        lines = code.split('\n')
        score = 0
        
        for line in lines:
            # Skip comments and empty lines
            if line.strip().startswith('#') or not line.strip():
                continue
                
            # Add points for control structures
            if any(keyword in line for keyword in ['if ', 'elif ', 'else:', 'for ', 'while ', 
                                                  'try:', 'except ', 'finally:', 'with ']):
                score += 1
            
            # Add points for logical operators
            if ' and ' in line or ' or ' in line:
                score += 0.5
            
            # Add points for function definitions
            if 'def ' in line:
                score += 1
            
            # Add points for class definitions
            if 'class ' in line:
                score += 2
        
        return int(score)
    
    def calculate_avg_indentation(self, code):
        """Calculate average indentation level"""
        lines = code.split('\n')
        indent_levels = []
        
        for line in lines:
            if line.strip():
                indent = len(line) - len(line.lstrip())
                indent_levels.append(indent // 4)  # Assuming 4-space indents
        
        return np.mean(indent_levels) if indent_levels else 0
    
    def calculate_max_nesting(self, code):
        """Calculate maximum nesting depth"""
        max_depth = 0
        current_depth = 0
        
        lines = code.split('\n')
        for line in lines:
            # Skip comments
            if line.strip().startswith('#'):
                continue
            
            # Count opening braces and colons
            line_depth = current_depth
            for char in line:
                if char == ':' and line.strip().endswith(':'):
                    line_depth += 1
                elif char == '(' or char == '[' or char == '{':
                    line_depth += 0.5  # Partial depth for brackets
            
            max_depth = max(max_depth, line_depth)
            
            # Reset for next line if not continuing
            if line.strip() and not line.strip().endswith(':'):
                current_depth = line_depth
        
        return max_depth
    
    def count_patterns(self, code):
        """Count pattern occurrences"""
        patterns = {
            'performance': {
                'range_len': len(re.findall(r'range\s*\(\s*len\s*\(', code, re.IGNORECASE)),
                'string_concat': len(re.findall(r'\w+\s*=\s*\w+\s*\+\s*["\']', code)),
                'list_comp_missing': len(re.findall(r'for\s+\w+\s+in\s+\w+\s*:', code)) - 
                                   len(re.findall(r'\[\s*.*?\s+for\s+.*?\s+in\s+.*?\]', code))
            },
            'style': {
                'bare_except': len(re.findall(r'except\s*:', code)),
                'print_statements': len(re.findall(r'print\s*\(', code)),
                'todo_comments': len(re.findall(r'#\s*(TODO|FIXME|HACK)', code, re.IGNORECASE))
            }
        }
        return patterns
    
    def predict_issues(self, code):
        """Predict potential issues using ML"""
        features = self.extract_features(code)
        
        predictions = []
        confidence_scores = {}
        
        # Analyze using trained patterns
        for category, patterns in self.pattern_model.items():
            for pattern_name, pattern_data in patterns.items():
                weight = pattern_data['weight']
                
                # Check if pattern exists in code
                if self.check_pattern_existence(code, pattern_name):
                    confidence = min(weight * 1.5, 0.95)  # Boost confidence
                    
                    prediction = {
                        'category': category,
                        'pattern': pattern_name,
                        'confidence': confidence,
                        'weight': weight,
                        'suggestion': self.get_suggestion(category, pattern_name)
                    }
                    
                    predictions.append(prediction)
                    confidence_scores[f"{category}_{pattern_name}"] = confidence
        
        # Sort by confidence
        predictions.sort(key=lambda x: x['confidence'], reverse=True)
        
        # Adjust weights based on predictions
        self.adjust_weights(code, predictions)
        
        return predictions[:10], confidence_scores
    
    def check_pattern_existence(self, code, pattern_name):
        """Check if a specific pattern exists in code"""
        pattern_checks = {
            'range_len_pattern': lambda c: bool(re.search(r'range\s*\(\s*len\s*\(', c)),
            'inefficient_concatenation': lambda c: bool(re.search(r'\w+\s*=\s*\w+\s*\+\s*["\']', c)),
            'list_membership': lambda c: bool(re.search(r'in\s+\[', c)),
            'redundant_bool': lambda c: bool(re.search(r'bool\s*\(.*?\)\s*==\s*(True|False)', c)),
            'bare_except': lambda c: bool(re.search(r'except\s*:', c)),
            'print_debugging': lambda c: bool(re.search(r'print\s*\(.*?(debug|test|temp)', c, re.IGNORECASE)),
            'eval_usage': lambda c: bool(re.search(r'eval\s*\(', c)),
            'exec_usage': lambda c: bool(re.search(r'exec\s*\(', c))
        }
        
        return pattern_checks.get(pattern_name, lambda c: False)(code)
    
    def get_suggestion(self, category, pattern_name):
        """Get suggestion for a pattern"""
        suggestions = {
            'range_len_pattern': 'Use enumerate() for index and value access',
            'inefficient_concatenation': 'Use str.join() for string concatenation in loops',
            'list_membership': 'Convert to set for faster membership testing',
            'redundant_bool': 'Direct boolean evaluation is cleaner',
            'bare_except': 'Specify exception types for better error handling',
            'print_debugging': 'Consider using logging module for debugging',
            'eval_usage': 'Avoid eval() - use ast.literal_eval() for safety',
            'exec_usage': 'exec() is a security risk - find alternatives'
        }
        return suggestions.get(pattern_name, 'Consider refactoring')
    
    def adjust_weights(self, code, predictions):
        """Adjust ML model weights based on findings"""
        for prediction in predictions:
            category = prediction['category']
            pattern = prediction['pattern']
            confidence = prediction['confidence']
            
            if pattern in self.pattern_model.get(category, {}):
                current_weight = self.pattern_model[category][pattern]['weight']
                
                # Adjust weight based on confidence and frequency
                adjustment = self.learning_rate * (confidence - current_weight)
                self.pattern_model[category][pattern]['weight'] = (
                    current_weight + adjustment
                )
                self.pattern_model[category][pattern]['count'] += 1
        
        # Periodically save the model
        if sum(p['confidence'] for p in predictions) > 2:
            self.save_model()

# ========================================================
# ENHANCED AI ANALYZER WITH ML
# ========================================================

class EnhancedAIAnalyzer:
    def __init__(self):
        self.ml_analyzer = MLCodeAnalyzer()
        self.patterns = self.initialize_patterns()
        self.history = []
        
    def initialize_patterns(self):
        return [
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
        """Analyze code with both rule-based and ML approaches"""
        suggestions = []
        
        # Get rule-based suggestions
        suggestions.extend(self.rule_based_analysis(code))
        
        # Get ML-based predictions
        ml_predictions, confidence_scores = self.ml_analyzer.predict_issues(code)
        suggestions.extend(self.ml_to_suggestions(ml_predictions))
        
        # Add code smell detection
        suggestions.extend(self.detect_code_smells(code))
        
        # Sort by priority and confidence
        suggestions.sort(key=lambda x: (
            {'high': 0, 'medium': 1, 'low': 2}.get(x['priority'], 3),
            -x.get('confidence', 0)
        ))
        
        # Store in history
        self.history.append({
            'timestamp': datetime.now().isoformat(),
            'suggestion_count': len(suggestions),
            'features': self.ml_analyzer.extract_features(code)
        })
        
        return suggestions[:20]
    
    def rule_based_analysis(self, code):
        """Traditional rule-based analysis"""
        suggestions = []
        
        for pattern, advice in self.patterns:
            matches = re.finditer(pattern, code)
            for match in matches:
                line_num = code[:match.start()].count('\n') + 1
                
                suggestion_text = f"Line {line_num}: {advice}"
                suggestions.append({
                    'line': line_num,
                    'suggestion': suggestion_text,
                    'category': self.get_category(pattern),
                    'priority': 'high' if '⚠️' in advice else 'medium',
                    'source': 'rule_based',
                    'confidence': 0.8
                })
        
        return suggestions
    
    def ml_to_suggestions(self, ml_predictions):
        """Convert ML predictions to suggestion format"""
        suggestions = []
        
        for pred in ml_predictions:
            suggestions.append({
                'line': 0,  # ML doesn't give line numbers
                'suggestion': f"[ML] {pred['suggestion']} (confidence: {pred['confidence']:.2f})",
                'category': pred['category'],
                'priority': 'high' if pred['confidence'] > 0.8 else 'medium' if pred['confidence'] > 0.5 else 'low',
                'source': 'ml',
                'confidence': pred['confidence']
            })
        
        return suggestions
    
    def detect_code_smells(self, code):
        """Detect common code smells"""
        suggestions = []
        lines = code.split('\n')
        
        # Long function detection
        function_start = -1
        for i, line in enumerate(lines):
            if line.strip().startswith('def '):
                if function_start != -1:
                    # Check previous function length
                    func_length = i - function_start
                    if func_length > 30:
                        suggestions.append({
                            'line': function_start + 1,
                            'suggestion': f"Long function detected ({func_length} lines). Consider splitting.",
                            'category': 'maintainability',
                            'priority': 'medium',
                            'source': 'heuristic',
                            'confidence': 0.7
                        })
                function_start = i
        
        # Deep nesting detection
        max_nesting = self.ml_analyzer.calculate_max_nesting(code)
        if max_nesting > 4:
            suggestions.append({
                'line': 0,
                'suggestion': f"Deep nesting detected (depth: {max_nesting}). Consider refactoring.",
                'category': 'complexity',
                'priority': 'medium',
                'source': 'heuristic',
                'confidence': 0.6
            })
        
        # Duplicate code detection (simplified)
        line_counts = Counter(lines)
        for line, count in line_counts.items():
            if count > 3 and len(line.strip()) > 20:
                suggestions.append({
                    'line': 0,
                    'suggestion': f"Possible duplicate code detected (occurs {count} times).",
                    'category': 'duplication',
                    'priority': 'low',
                    'source': 'heuristic',
                    'confidence': 0.5
                })
        
        return suggestions
    
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
    
    def get_advanced_metrics(self, code):
        """Get advanced ML-based metrics"""
        features = self.ml_analyzer.extract_features(code)
        
        metrics = {
            'total_lines': features.get('line_count', 0),
            'avg_indentation': features.get('indentation_depth', 0),
            'max_nesting': features.get('nesting_depth', 0),
            'complexity_score': features.get('complexity_score', 0),
            'function_count': features.get('function_count', 0),
            'class_count': features.get('class_count', 0),
            'quality_score': self.calculate_quality_score(features),
            'patterns_detected': sum(features.get(f'{cat}_{pat}', 0) 
                                   for cat in ['performance', 'style'] 
                                   for pat in ['range_len', 'bare_except', 'todo_comments'])
        }
        
        return metrics
    
    def calculate_quality_score(self, features):
        """Calculate overall code quality score (0-100)"""
        score = 100
        
        # Penalize for complexity
        complexity = features.get('complexity_score', 0)
        score -= min(complexity * 2, 30)
        
        # Penalize for deep nesting
        nesting = features.get('nesting_depth', 0)
        score -= min(nesting * 5, 20)
        
        # Penalize for anti-patterns
        anti_patterns = sum(
            features.get(f'{cat}_{pat}', 0) 
            for cat in ['performance', 'style'] 
            for pat in ['range_len', 'bare_except']
        )
        score -= min(anti_patterns * 3, 25)
        
        # Bonus for functions and classes
        functions = features.get('function_count', 0)
        classes = features.get('class_count', 0)
        score += min((functions + classes) * 2, 15)
        
        return max(0, min(100, score))

# ========================================================
# ENHANCED EDITOR WITH ML
# ========================================================

class AIPythonEditorWithML:
    def __init__(self, root):
        self.root = root
        self.root.title("🤖 AI Python Editor with ML")
        self.root.geometry("1400x800")
        
        # Initialize enhanced analyzer with ML
        self.ai_analyzer = EnhancedAIAnalyzer()
        
        self.setup_ui()
        
    def setup_ui(self):
        # Create main container with more space
        main_container = tk.PanedWindow(self.root, orient=tk.HORIZONTAL, sashwidth=5)
        main_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Left: Editor panel (60%)
        left_panel = tk.Frame(main_container)
        self.setup_editor_panel(left_panel)
        main_container.add(left_panel, minsize=400)
        
        # Middle: AI Suggestions panel (30%)
        middle_panel = tk.Frame(main_container)
        self.setup_suggestions_panel(middle_panel)
        main_container.add(middle_panel, minsize=300)
        
        # Right: ML Insights panel (30%)
        right_panel = tk.Frame(main_container)
        self.setup_ml_panel(right_panel)
        main_container.add(right_panel, minsize=300)
        
        # Initial analysis (commented out to prevent error on startup)
        self.update_line_numbers()
        # Uncomment after testing
        self.analyze_with_ai()
    
    def setup_editor_panel(self, parent):
        """Setup the code editor panel"""
        # Editor with line numbers
        editor_container = tk.Frame(parent)
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
                                               undo=True, wrap=tk.WORD)
        self.editor.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Add sample code
        self.insert_ml_sample_code()
        
        # Bind events
        self.editor.bind("<KeyRelease>", self.on_editor_change)
        
        # Toolbar
        toolbar = tk.Frame(parent, bg="#2D3748", height=40)
        toolbar.pack(fill=tk.X, pady=(5, 0))
        
        # Toolbar buttons
        buttons = [
            ("▶ Run", self.run_code, "#48BB78"),
            ("🤖 Analyze", self.analyze_with_ai, "#9F7AEA"),
            ("🧠 ML Train", self.train_ml_model, "#805AD5"),
            ("💾 Save", self.save_file, "#4299E1"),
            ("📂 Open", self.open_file, "#ED8936"),
            ("📊 Stats", self.show_statistics, "#38B2AC"),
            ("🗑 Clear", self.clear_editor, "#F56565"),
        ]
        
        for text, command, color in buttons:
            btn = tk.Button(toolbar, text=text, command=command,
                           bg=color, fg="white", font=("Arial", 9, "bold"),
                           padx=10, pady=3)
            btn.pack(side=tk.LEFT, padx=2)
        
        # Auto-analyze toggle
        self.auto_analyze = tk.BooleanVar(value=True)
        tk.Checkbutton(toolbar, text="Auto-analyze",
                      variable=self.auto_analyze,
                      fg="white", bg="#2D3748").pack(side=tk.RIGHT, padx=10)
    
    def setup_suggestions_panel(self, parent):
        """Setup AI suggestions panel"""
        # AI Recommendations
        ai_frame = tk.LabelFrame(parent, text="🧠 AI Suggestions",
                                font=("Arial", 12, "bold"))
        ai_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Source filter
        filter_frame = tk.Frame(ai_frame, bg="#2D3748")
        filter_frame.pack(fill=tk.X, padx=5, pady=5)
        
        tk.Label(filter_frame, text="Filter:", bg="#2D3748", fg="white").pack(side=tk.LEFT)
        
        self.filter_var = tk.StringVar(value="all")
        sources = [("All", "all"), ("ML", "ml"), ("Rules", "rule_based")]
        
        for text, value in sources:
            tk.Radiobutton(filter_frame, text=text, variable=self.filter_var,
                          value=value, bg="#2D3748", fg="white",
                          selectcolor="#4FD1C7",
                          command=self.refilter_suggestions).pack(side=tk.LEFT, padx=5)
        
        # Recommendation list
        list_frame = tk.Frame(ai_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.recommendation_list = tk.Listbox(list_frame,
                                             yscrollcommand=scrollbar.set,
                                             bg="#2D3748",
                                             fg="white",
                                             font=("Arial", 9),
                                             selectbackground="#4FD1C7",
                                             height=20)
        self.recommendation_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.recommendation_list.yview)
        
        # Bind double-click
        self.recommendation_list.bind("<Double-Button-1>", self.show_suggestion_detail)
        
        # Action buttons
        action_frame = tk.Frame(ai_frame)
        action_frame.pack(fill=tk.X, padx=5, pady=5)
        
        tk.Button(action_frame, text="Apply",
                 command=self.apply_suggestion,
                 bg="#38B2AC", fg="white").pack(side=tk.LEFT, padx=2)
        
        tk.Button(action_frame, text="Ignore",
                 command=self.ignore_suggestion,
                 bg="#F56565", fg="white").pack(side=tk.LEFT, padx=2)
        
        tk.Button(action_frame, text="Clear",
                 command=self.clear_suggestions,
                 bg="#718096", fg="white").pack(side=tk.RIGHT, padx=2)
    
    def setup_ml_panel(self, parent):
        """Setup ML insights panel"""
        # ML Insights
        ml_frame = tk.LabelFrame(parent, text="🤖 ML Insights",
                                font=("Arial", 12, "bold"))
        ml_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Model info
        info_frame = tk.Frame(ml_frame)
        info_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.model_info = tk.Text(info_frame, height=4,
                                 bg="#2D3748", fg="white",
                                 font=("Consolas", 9))
        self.model_info.pack(fill=tk.BOTH, expand=True)
        self.model_info.config(state='disabled')
        
        # Advanced metrics
        metrics_frame = tk.LabelFrame(ml_frame, text="📈 Advanced Metrics",
                                     font=("Arial", 10, "bold"))
        metrics_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.metrics_text = tk.Text(metrics_frame, height=12,
                                   bg="#2D3748", fg="white",
                                   font=("Consolas", 9))
        self.metrics_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.metrics_text.config(state='disabled')
        
        # Output Panel
        output_frame = tk.LabelFrame(parent, text="📤 Output",
                                    font=("Arial", 12, "bold"))
        output_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.output_text = scrolledtext.ScrolledText(output_frame,
                                                    bg="black", fg="#00FF00",
                                                    font=("Consolas", 10))
        self.output_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    def insert_ml_sample_code(self):
        """Insert sample code with ML-detectable patterns"""
        sample_code = '''# ML-Enhanced Python Editor Demo
# This code contains various patterns for ML detection

class DataProcessor:
    """Process data with various operations"""
    
    def __init__(self, data):
        self.data = data
        self.results = []
    
    def process_data_inefficient(self):
        """Inefficient processing with common patterns"""
        # Pattern 1: range(len()) - ML will detect this
        for i in range(len(self.data)):
            item = self.data[i]
            # Pattern 2: String concatenation in loop
            output = ""
            for char in item:
                output = output + char  # Inefficient!
            self.results.append(output)
        
        # Pattern 3: List membership test
        if "target" in ["item1", "item2", "target", "item3"]:
            print("Found target")
        
        return self.results
    
    def better_processing(self):
        """More efficient version"""
        results = []
        for item in self.data:  # Better: direct iteration
            # Better: join for string concatenation
            output = ''.join(item)
            results.append(output)
        
        # Better: set for membership test
        items_set = {"item1", "item2", "target", "item3"}
        if "target" in items_set:
            print("Found target efficiently")
        
        return results

def redundant_checks(x):
    """Function with redundant boolean checks"""
    # ML will detect redundant bool()
    if bool(x > 0) == True:
        return True
    elif bool(x < 0) == False:
        return False
    else:
        return None

# TODO: Add more functionality here
# FIXME: Implement error handling
# HACK: Temporary solution

def main():
    """Main execution"""
    data = ["abc", "def", "ghi"]
    processor = DataProcessor(data)
    
    # Try both methods
    print("Inefficient method:")
    result1 = processor.process_data_inefficient()
    print(result1)
    
    print("\nBetter method:")
    result2 = processor.better_processing()
    print(result2)
    
    # Test redundant checks
    print("\nRedundant checks:", redundant_checks(5))

if __name__ == "__main__":
    main()'''
        
        self.editor.insert("1.0", sample_code)
    
    def analyze_with_ai(self):
        """Analyze code with enhanced AI"""
        try:
            code = self.editor.get("1.0", tk.END)
            
            # Get enhanced suggestions
            suggestions = self.ai_analyzer.analyze_code(code)
            
            # Get advanced metrics
            metrics = self.ai_analyzer.get_advanced_metrics(code)
            
            # Update UI
            self.update_suggestions_list(suggestions)
            self.update_ml_display(metrics)
            self.update_model_info()
        except Exception as e:
            # Handle errors gracefully
            print(f"Analysis error: {e}")
            self.output_text.insert(tk.END, f"\n⚠️ Analysis error: {e}\n")
    
    def update_suggestions_list(self, suggestions):
        """Update the suggestions listbox with filtering"""
        self.recommendation_list.delete(0, tk.END)
        self.all_suggestions = suggestions
        
        if not suggestions:
            self.recommendation_list.insert(0, "✅ No suggestions - code looks good!")
            return
        
        # Filter suggestions
        filter_source = self.filter_var.get()
        filtered_suggestions = [
            s for s in suggestions
            if filter_source == "all" or s.get('source') == filter_source
        ]
        
        for i, suggestion in enumerate(filtered_suggestions, 1):
            # Color and emoji based on priority and source
            source_emoji = "🤖" if suggestion.get('source') == 'ml' else "📝"
            
            emoji = {
                'high': '🔴',
                'medium': '🟡',
                'low': '🟢'
            }.get(suggestion['priority'], '⚪')
            
            # Truncate and format
            text = suggestion['suggestion']
            if len(text) > 50:
                text = text[:47] + "..."
            
            confidence = suggestion.get('confidence', 0)
            if confidence > 0:
                text += f" [{confidence:.2f}]"
            
            display_text = f"{source_emoji}{emoji} {text}"
            self.recommendation_list.insert(tk.END, display_text)
            
            # Color the item
            color = {
                'high': '#F56565',
                'medium': '#ECC94B',
                'low': '#48BB78'
            }.get(suggestion['priority'], 'white')
            
            self.recommendation_list.itemconfig(tk.END, {'fg': color})
    
    def update_ml_display(self, metrics):
        """Update ML metrics display"""
        self.metrics_text.config(state='normal')
        self.metrics_text.delete("1.0", tk.END)
        
        # Create quality gauge
        quality = metrics.get('quality_score', 0)
        gauge = self.create_quality_gauge(quality)
        
        report = f"""🤖 ADVANCED CODE ANALYSIS
{'='*40}

{gauge}

📊 METRICS:
{'─'*30}
Total Lines: {metrics.get('total_lines', 0)}
Functions: {metrics.get('function_count', 0)}
Classes: {metrics.get('class_count', 0)}
Avg Indentation: {metrics.get('avg_indentation', 0):.1f}
Max Nesting Depth: {metrics.get('max_nesting', 0)}
Complexity Score: {metrics.get('complexity_score', 0)}
Patterns Detected: {metrics.get('patterns_detected', 0)}

📈 QUALITY SCORE: {quality}/100
{'⚠️ Needs improvement' if quality < 50 else '🟡 Good' if quality < 80 else '✅ Excellent'}
"""
        
        self.metrics_text.insert("1.0", report)
        self.metrics_text.config(state='disabled')
    
    def update_model_info(self):
        """Update ML model information"""
        self.model_info.config(state='normal')
        self.model_info.delete("1.0", tk.END)
        
        try:
            model = self.ai_analyzer.ml_analyzer.pattern_model
            
            info = "🧠 ML MODEL STATUS\n"
            info += "="*30 + "\n\n"
            
            total_patterns = sum(
                len(category) for category in model.values()
            )
            info += f"Patterns learned: {total_patterns}\n"
            
            # Show top patterns by weight
            info += "\nTop patterns (by weight):\n"
            all_patterns = []
            for category, patterns in model.items():
                for pattern, data in patterns.items():
                    all_patterns.append((category, pattern, data['weight'], data['count']))
            
            all_patterns.sort(key=lambda x: x[2], reverse=True)
            
            for category, pattern, weight, count in all_patterns[:5]:
                info += f"  • {category}.{pattern}: {weight:.2f} ({count}×)\n"
            
            history_len = len(self.ai_analyzer.history)
            info += f"\nAnalysis history: {history_len} entries"
            
            self.model_info.insert("1.0", info)
        except Exception as e:
            self.model_info.insert("1.0", f"Model info error: {e}")
        
        self.model_info.config(state='disabled')
    
    def create_quality_gauge(self, score):
        """Create ASCII quality gauge"""
        filled = int(score / 5)
        empty = 20 - filled
        
        gauge = "["
        gauge += "█" * filled
        gauge += "░" * empty
        gauge += f"] {score}%"
        
        return gauge
    
    def train_ml_model(self):
        """Train ML model with current code"""
        code = self.editor.get("1.0", tk.END)
        
        try:
            # Force analysis to update model weights
            self.ai_analyzer.ml_analyzer.predict_issues(code)
            self.ai_analyzer.ml_analyzer.save_model()
            
            self.output_text.insert(tk.END, "\n🧠 ML model trained with current code patterns\n")
            self.update_model_info()
            messagebox.showinfo("ML Training", "Model trained with current code patterns!")
        except Exception as e:
            messagebox.showerror("Training Error", f"Error training model: {e}")
    
    def show_statistics(self):
        """Show analysis statistics"""
        stats_window = tk.Toplevel(self.root)
        stats_window.title("📊 Analysis Statistics")
        stats_window.geometry("500x400")
        
        stats_text = scrolledtext.ScrolledText(stats_window,
                                              bg="#2D3748", fg="white",
                                              font=("Consolas", 10))
        stats_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        history = self.ai_analyzer.history
        if not history:
            stats_text.insert(tk.END, "No analysis history yet.")
        else:
            stats_text.insert(tk.END, "📊 ANALYSIS HISTORY\n")
            stats_text.insert(tk.END, "="*50 + "\n\n")
            
            for entry in history[-10:]:  # Show last 10 entries
                timestamp = entry['timestamp'][11:19]  # Just time
                count = entry['suggestion_count']
                features = entry['features']
                
                stats_text.insert(tk.END, f"{timestamp} - {count} suggestions\n")
                stats_text.insert(tk.END, f"  Lines: {features.get('line_count', 0)}")
                stats_text.insert(tk.END, f" | Functions: {features.get('function_count', 0)}")
                stats_text.insert(tk.END, f" | Complexity: {features.get('complexity_score', 0)}\n\n")
        
        stats_text.config(state='disabled')
    
    def refilter_suggestions(self):
        """Re-filter suggestions based on current filter"""
        if hasattr(self, 'all_suggestions'):
            self.update_suggestions_list(self.all_suggestions)
    
    def ignore_suggestion(self):
        """Ignore selected suggestion"""
        selection = self.recommendation_list.curselection()
        if not selection:
            return
        
        # Remove from list
        index = selection[0]
        self.recommendation_list.delete(index)
        
        if self.recommendation_list.size() == 0:
            self.recommendation_list.insert(0, "All suggestions ignored")
    
    def show_suggestion_detail(self, event):
        """Show detailed view of suggestion"""
        selection = self.recommendation_list.curselection()
        if not selection:
            return
        
        index = selection[0]
        if hasattr(self, 'all_suggestions') and index < len(self.all_suggestions):
            suggestion = self.all_suggestions[index]
            
            detail_window = tk.Toplevel(self.root)
            detail_window.title(f"Suggestion Details")
            detail_window.geometry("600x400")
            
            # Title
            title_text = f"{suggestion['category'].upper()} Suggestion"
            if suggestion.get('line') > 0:
                title_text += f" - Line {suggestion['line']}"
            
            title = tk.Label(detail_window, 
                            text=title_text,
                            font=("Arial", 12, "bold"))
            title.pack(pady=10)
            
            # Priority and source
            source_text = f"Source: {suggestion.get('source', 'unknown')} | Priority: {suggestion['priority'].upper()}"
            if suggestion.get('confidence') > 0:
                source_text += f" | Confidence: {suggestion['confidence']:.2f}"
            
            source_label = tk.Label(detail_window, text=source_text, font=("Arial", 10))
            source_label.pack(pady=5)
            
            # Suggestion text
            text_frame = tk.Frame(detail_window)
            text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            suggestion_text = tk.Text(text_frame, wrap=tk.WORD, font=("Arial", 10))
            suggestion_text.pack(fill=tk.BOTH, expand=True)
            suggestion_text.insert("1.0", suggestion['suggestion'])
            suggestion_text.config(state='disabled')
            
            # Action buttons
            button_frame = tk.Frame(detail_window)
            button_frame.pack(pady=10)
            
            tk.Button(button_frame, text="Close",
                     command=detail_window.destroy).pack(side=tk.LEFT, padx=5)
            
            if suggestion.get('line') > 0:
                tk.Button(button_frame, text="Go to Line",
                         command=lambda: self.goto_line(suggestion['line'])).pack(side=tk.LEFT, padx=5)
    
    def goto_line(self, line_num):
        """Navigate to a specific line in editor"""
        self.editor.focus_set()
        self.editor.mark_set("insert", f"{line_num}.0")
        self.editor.see(f"{line_num}.0")
    
    def apply_suggestion(self):
        """Apply selected suggestion to code"""
        selection = self.recommendation_list.curselection()
        if not selection:
            messagebox.showinfo("Info", "Select a suggestion first!")
            return
        
        index = selection[0]
        if hasattr(self, 'all_suggestions') and index < len(self.all_suggestions):
            suggestion = self.all_suggestions[index]
            
            if suggestion.get('line') > 0:
                # Get the line
                code = self.editor.get("1.0", tk.END)
                lines = code.split('\n')
                
                if suggestion['line'] <= len(lines):
                    current_line = lines[suggestion['line'] - 1]
                    messagebox.showinfo("Apply Suggestion",
                                      f"Line {suggestion['line']}:\n{current_line}\n\n"
                                      f"Suggestion: {suggestion['suggestion']}")
            else:
                messagebox.showinfo("ML Suggestion", 
                                  f"ML Suggestion:\n{suggestion['suggestion']}\n\n"
                                  f"Confidence: {suggestion.get('confidence', 0):.2f}")
    
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
            self.root.title(f"AI Python Editor with ML - {os.path.basename(filepath)}")
    
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
            self.root.title(f"AI Python Editor with ML - {os.path.basename(filepath)}")
    
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
    
    def update_line_numbers(self):
        """Update line numbers display"""
        lines = self.editor.get("1.0", tk.END).count("\n")
        
        self.line_numbers.config(state='normal')
        self.line_numbers.delete("1.0", tk.END)
        
        for i in range(1, lines + 1):
            self.line_numbers.insert(tk.END, f"{i}\n")
        
        self.line_numbers.config(state='disabled')
    
    def on_editor_change(self, event=None):
        """Handle editor changes"""
        self.update_line_numbers()
        
        # Auto-analyze if enabled
        if self.auto_analyze.get():
            code = self.editor.get("1.0", tk.END)
            if len(code.strip()) > 10:  # Only if there's actual code
                self.root.after(1000, self.analyze_with_ai)  # Delay 1 second

def main():
    root = tk.Tk()
    editor = AIPythonEditorWithML(root)
    root.mainloop()

if __name__ == "__main__":
    main()