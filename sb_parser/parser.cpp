#include <iostream>
#include <fstream>
#include <string>
#include <vector>

#include "block.hpp"
#include "hasher.hpp"

typedef enum {
	STATE_IDLE,
	STATE_READING_NAME,
	STATE_READING_ATTR
} state_t;

Block* parse_sb_file(std::ifstream& stream, StringHasher &hasher) {
	Block* root = new Block(hasher);
	root->set_name("root");
	
	std::vector<Block*> block_stack;
	block_stack.push_back(root);

	state_t state = STATE_IDLE;
	std::string curr_token = "";

	while (!stream.eof()) {
		char c = stream.get();	

		// brackets mean changing current block
		if (c == '(' || c == ')') {
			if (!curr_token.empty()) {
				if (state == STATE_READING_NAME) {
					block_stack.back()->set_name(curr_token);
					state = STATE_READING_ATTR;
				}
				else if (state == STATE_READING_ATTR) {
					block_stack.back()->add_attr(curr_token);
				}

				curr_token.clear();
			}

			state = STATE_READING_NAME;
			if (c == '(') {
				Block *new_block = new Block(hasher);
				block_stack.push_back(new_block);
			}
			else {
				Block *current_block_ptr = block_stack.back();
				block_stack.pop_back();

				if (!block_stack.empty()) {
					Block *prev_block_ptr = block_stack.back();
					prev_block_ptr->add_child(current_block_ptr);
				}
			}
			
			continue;
		}

		// space means token end
		if (c == ' ' || c == '\n' || c == '\t') {
			if (curr_token.empty()) {
				continue;
			}

			if (state == STATE_READING_NAME) {
				block_stack.back()->set_name(curr_token);
				state = STATE_READING_ATTR;
			}
			else if (state == STATE_READING_ATTR) {
				block_stack.back()->add_attr(curr_token);
			}

			curr_token.clear();
			continue;
		}

		curr_token += c;
	}

	return root;
}

int main(int argc, char **argv) {
	if (argc < 3) {
		std::cerr << "Usage: " << argv[0] << " file1.sb file2.sb" << std::endl;
		return 1;
	}

	std::ifstream file1(argv[1]);
	if (!file1.is_open()) {
		std::cerr << "Unable to open file: '" << argv[1] << "'" << std::endl;
		return 1;
	}

	std::ifstream file2(argv[2]);
	if (!file2.is_open()) {
		std::cerr << "Unable to open file: '" << argv[2] << "'" << std::endl;
		return 1;
	}

	StringHasher main_hasher;

	Block *root1 = parse_sb_file(file1, main_hasher);
	Block *root2 = parse_sb_file(file2, main_hasher);

	int retcode = 0;
	if (root1->compare_to(root2) != 0) {
		retcode = 1;
	}

	delete root1;
	delete root2;

	return retcode;
}