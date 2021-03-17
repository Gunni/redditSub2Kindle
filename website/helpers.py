import re

import nltk as nltk
from word2number import w2n

# Takes in string containing "numberwords" and returns it with those "numberwords" replaced with digits
# Examples:
# 'Hello one two three' becomes 'Hello 123'
def replaceTextnumberWithNumber(text):
	tagged_number_words = 'ten/CD thousand/CD nine/CD hundred/CD ninety/CD eight/CD seven/CD six/CD five/CD four/CD three/CD two/CD one/CD eighty/CD seventy/CD sixty/CD fifty/CD forty/CD thirty/CD twenty/CD nineteen/CD eighteen/CD seventeen/CD sixteen/CD fifteen/CD fourteen/CD thirteen/CD twelve/CD eleven/CD zero/CD'
	tagged_number_words_tuples = [nltk.tag.str2tuple(t) for t in tagged_number_words.split()]
	my_tagger = nltk.UnigramTagger([ tagged_number_words_tuples ], backoff=nltk.DefaultTagger('IGNORE'))

	my_grammar = 'NumberWord: {<CD>+}'
	parser = nltk.RegexpParser(my_grammar)
	parsed = parser.parse(my_tagger.tag(nltk.word_tokenize(text.lower())))

	for tag in [tree.leaves() for tree in parsed.subtrees() if tree.label() == 'NumberWord']:
		ut = nltk.untag(tag)
		num = w2n.word_to_num(' '.join(ut))

		r = re.compile(re.escape(' '.join(ut)), re.IGNORECASE)
		text = r.sub(str(num), text)

	return text
