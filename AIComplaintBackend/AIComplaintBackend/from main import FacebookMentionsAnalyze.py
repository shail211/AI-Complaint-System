from main import FacebookMentionsAnalyzer

# Initialize system
analyzer = FacebookMentionsAnalyzer()

# Run analysis
posts, file = analyzer.analyze_mentions(days=7, save_json=True)

# View complaints only
analyzer.print_complaints_only(file)
