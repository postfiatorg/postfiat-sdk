/**
 * PostFiat TypeScript SDK: Envelope Factory Example
 * 
 * This example demonstrates how to use the EnvelopeFactory for automatic
 * size validation and chunking of large content.
 */

import { 
  EnvelopeFactory,
  IPFSStorage,
  MultipartStorage,
  EnvelopeValidationError
} from '../src/envelope';
import { EncryptionMode } from '../src/types/enums';
import { PostFiatCrypto } from '../src/crypto';
import { Envelope, ContentDescriptor } from '../src/generated/postfiat/v3/messages_pb';

async function demonstrateEnvelopeFactory() {
  console.log('🔧 PostFiat TypeScript SDK: Envelope Factory Example');
  console.log('=' + '='.repeat(55));

  try {
    // 1. Generate key pair for encryption
    console.log('\n1. Generating cryptographic key pair...');
    const keyPair = await PostFiatCrypto.generateKeyPair();
    console.log(`   Public Key: ${keyPair.publicKey.substring(0, 32)}...`);
    console.log(`   Private Key: ${keyPair.privateKey.substring(0, 32)}...`);

    // 2. Create envelope factory with 1000 byte limit and IPFS storage
    console.log('\n2. Creating envelope factory with 1000 byte limit and IPFS storage...');
    const factory = new EnvelopeFactory(1000, new IPFSStorage());

    // 3. Test with small content (should create single envelope)
    console.log('\n3. Testing with small content...');
    const smallContent = 'What are the latest developments in AI ethics research?';
    
    const smallResult = await factory.createEnvelope(
      smallContent,
      keyPair.privateKey,
      keyPair.publicKey,
      EncryptionMode.PUBLIC_KEY
    );

    if (smallResult instanceof Envelope) {
      console.log(`   ✅ Single envelope created for small content`);
      console.log(`   Envelope size: ${smallResult.serializeBinary().length} bytes`);
    } else if (Array.isArray(smallResult)) {
      const [envelope, descriptor] = smallResult;
      console.log(`   ✅ Content stored externally via ${descriptor.getUri()}`);
      console.log(`   Envelope size: ${envelope.serializeBinary().length} bytes`);
    } else {
      console.log(`   ❌ Unexpected result type for small content`);
    }

    // 4. Test with large content (should create chunked envelopes)
    console.log('\n4. Testing with large content...');
    const largeContent = 'AI ethics research has rapidly evolved in recent years, encompassing a broad spectrum of considerations that span technical, philosophical, legal, and societal dimensions. ' +
      'The field emerged from growing recognition that artificial intelligence systems, while offering tremendous potential for benefit, also pose significant risks if developed and deployed without careful ethical consideration. ' +
      'Key areas of focus include algorithmic bias and fairness, where researchers work to identify and mitigate discriminatory outcomes that can arise from biased training data or flawed model architectures. ' +
      'Privacy and data protection represent another critical domain, particularly as AI systems increasingly rely on vast datasets that may contain sensitive personal information. ' +
      'Transparency and explainability have become central concerns, especially for high-stakes applications in healthcare, criminal justice, and financial services, where stakeholders need to understand how AI systems reach their decisions. ' +
      'The question of AI accountability remains complex, involving considerations of liability, responsibility, and governance frameworks for autonomous systems. ' +
      'Additionally, researchers are grappling with longer-term considerations around artificial general intelligence, including questions of AI safety, alignment with human values, and the potential societal impacts of increasingly capable AI systems.';

    const largeResult = await factory.createEnvelope(
      largeContent,
      keyPair.privateKey,
      keyPair.publicKey,
      EncryptionMode.PUBLIC_KEY
    );

    if (largeResult instanceof Envelope) {
      console.log(`   ✅ Single envelope created for large content`);
      console.log(`   Envelope size: ${largeResult.serializeBinary().length} bytes`);
    } else if (Array.isArray(largeResult)) {
      const [envelope, descriptor] = largeResult;
      console.log(`   ✅ Large content stored externally via ${descriptor.getUri()}`);
      console.log(`   Content type: ${descriptor.getContentType()}`);
      console.log(`   Content length: ${descriptor.getContentLength()} bytes`);
      console.log(`   Envelope size: ${envelope.serializeBinary().length} bytes`);
    } else if (largeResult instanceof Set) {
      console.log(`   ✅ Content automatically chunked into ${largeResult.size} envelopes`);
      
      // Display chunk information
      const envelopes = Array.from(largeResult);
      envelopes.forEach((envelope, index) => {
        const chunkInfo = envelope.getMetadataMap().get('multipart') || 'unknown';
        const size = envelope.serializeBinary().length;
        console.log(`   Chunk ${index + 1}: ${chunkInfo}, size: ${size} bytes`);
      });

      // 5. Demonstrate content reconstruction
      console.log('\n5. Reconstructing content from chunks...');
      const reconstructed = await EnvelopeFactory.reconstructContentFromChunks(envelopes);
      
      const isValid = reconstructed === largeContent;
      console.log(`   ✅ Content reconstruction: ${isValid ? 'SUCCESS' : 'FAILED'}`);
      console.log(`   Original length: ${largeContent.length}`);
      console.log(`   Reconstructed length: ${reconstructed.length}`);
    } else {
      console.log(`   ❌ Unexpected result type for large content`);
    }

    // 6. Test size validation error
    console.log('\n6. Testing size validation with extremely large content...');
    const extremelyLargeContent = 'A'.repeat(10000); // 10KB content
    
    try {
      await factory.createEnvelope(
        extremelyLargeContent,
        keyPair.privateKey,
        keyPair.publicKey,
        EncryptionMode.PUBLIC_KEY
      );
      console.log(`   ❌ Expected validation error for extremely large content`);
    } catch (error) {
      if (error instanceof EnvelopeValidationError) {
        console.log(`   ✅ Validation error caught: ${error.message}`);
      } else {
        console.log(`   ❌ Unexpected error type: ${error.constructor.name}`);
      }
    }

    // 7. Test with MultipartStorage for on-ledger chunking
    console.log('\n7. Testing with MultipartStorage for on-ledger chunking...');
    const multipartFactory = new EnvelopeFactory(1000, new MultipartStorage());
    
    const multipartResult = await multipartFactory.createEnvelope(
      largeContent,
      keyPair.privateKey,
      keyPair.publicKey,
      EncryptionMode.PUBLIC_KEY
    );

    if (multipartResult instanceof Set) {
      console.log(`   ✅ Content chunked into ${multipartResult.size} envelopes for ledger storage`);
      
      const envelopes = Array.from(multipartResult);
      envelopes.forEach((envelope, index) => {
        const chunkInfo = envelope.getMetadataMap().get('multipart') || 'unknown';
        const messageId = envelope.getMetadataMap().get('message_id') || 'unknown';
        const size = envelope.serializeBinary().length;
        console.log(`   Chunk ${index + 1}: ${chunkInfo}, message_id: ${messageId.substring(0, 8)}..., size: ${size} bytes`);
      });
    } else {
      console.log(`   ❌ Expected multipart chunking for large content`);
    }

    console.log('\n✅ Envelope Factory example complete!');
    console.log('\nKey features demonstrated:');
    console.log('- Automatic size validation with 1000 byte limit');
    console.log('- IPFS storage for external content');
    console.log('- Multipart storage for on-ledger chunking');
    console.log('- Content reconstruction from chunks');
    console.log('- Proper error handling for oversized content');
    console.log('- Integration with PostFiat crypto system');

  } catch (error) {
    console.error('\n❌ Example failed:', error);
  }
}

// Run the example
if (require.main === module) {
  demonstrateEnvelopeFactory().catch(console.error);
}

export { demonstrateEnvelopeFactory };