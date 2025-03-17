import https from 'https';
import { TokenTracker } from "../utils/token-tracker";

import { SearchResponse } from '../types';
import {JINA_API_KEY} from "../config";

export function jinaSearch(query: string, tracker?: TokenTracker): Promise<{ response: SearchResponse, tokens: number }> {
  return new Promise((resolve, reject) => {
    if (!query.trim()) {
      reject(new Error('Query cannot be empty'));
      return;
    }

    const options = {
      hostname: 's.jina.ai',
      port: 443,
      path: `/${encodeURIComponent(query)}?count=0`,
      method: 'GET',
      headers: {
        'Accept': 'application/json',
        'Authorization': `Bearer ${JINA_API_KEY}`,
        'X-Retain-Images': 'none'
      }
    };

    const req = https.request(options, (res) => {
      let responseData = '';
      res.on('data', (chunk) => responseData += chunk);
      res.on('end', () => {
        const response = JSON.parse(responseData) as SearchResponse;

        if (!query.trim()) {
          reject(new Error('Query cannot be empty'));
          return;
        }

        if (response.code === 402) {
          reject(new Error(response.readableMessage || 'Insufficient balance'));
          return;
        }

        if (!response.data || !Array.isArray(response.data)) {
          reject(new Error('Invalid response format'));
          return;
        }

        const totalTokens = response.data.reduce((sum, item) => sum + (item.usage?.tokens || 0), 0);
        console.log('Total URLs:', response.data.length);
        (tracker || new TokenTracker()).trackUsage('search', totalTokens);
        resolve({ response, tokens: totalTokens });
      });
    });

    req.on('error', reject);
    req.end();
  });
}
