// Copy a file
#include <fstream>      // std::ifstream, std::ofstream
#include <iostream>
#include <stdlib.h>   
#include <random>

// Just generate samples and put it in a file. 

// Compile with 
// g++ generate-samples.cc  -std=c++11 -o generate-samples

int main() {
	std::default_random_engine generator;
  	std::uniform_real_distribution<float> distribution(-1.0,1.0);

 	std::ofstream out("testdata.bin", std::ios_base::binary | std::ios_base::app);
 	/* initialize random seed: */
	if (out.is_open()){
		for (int i = 0; i < 1000; i++) {
			float val = distribution(generator);
			std::cout<<val << "\n";
			out.write((char*)&val, sizeof(float));
		}
	    out.close();
	}
	
 	std::ifstream in("testdata.bin",std::ios_base::binary);
	if(in.is_open()) {
	   	for (int i = 0; i < 1000; i++) {
			float f2;
    			in.read((char *)&f2,sizeof(float));
    			std::cout << "Reading floating point number: " << std::fixed << f2 << std::endl;
		}
  	}
	
}
