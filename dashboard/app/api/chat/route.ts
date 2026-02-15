import Anthropic from '@anthropic-ai/sdk';
import { NextRequest, NextResponse } from 'next/server';

const anthropic = new Anthropic({
  apiKey: process.env.ANTHROPIC_API_KEY,
});

export async function POST(request: NextRequest) {
  try {
    const { message, preferences } = await request.json();

    if (!message) {
      return NextResponse.json(
        { error: 'Message is required' },
        { status: 400 }
      );
    }

    // Build system prompt with user preferences
    const preferencesText = preferences && preferences.length > 0
      ? `The user has the following dietary preferences and restrictions: ${preferences.join(', ')}.`
      : 'The user has no specific dietary preferences.';

    const systemPrompt = `You are a helpful cooking assistant. ${preferencesText}

When the user asks what to cook or requests meal recommendations, provide 3 specific meal suggestions that match their preferences and request.

Return your response in the following JSON format:
{
  "recommendations": [
    {
      "name": "Meal Name",
      "description": "Brief description of the dish",
      "imageUrl": "/images/dishes/placeholder.png"
    }
  ],
  "message": "A friendly response to the user's request"
}

Make sure the meal names are specific and appealing. Consider the user's preferences when making recommendations.`;

    const response = await anthropic.messages.create({
      model: 'claude-sonnet-4-20250514',
      max_tokens: 1024,
      system: systemPrompt,
      messages: [
        {
          role: 'user',
          content: message,
        },
      ],
    });

    // Extract the text content from Claude's response
    const textContent = response.content[0];
    if (textContent.type !== 'text') {
      throw new Error('Unexpected response format from Claude');
    }

    // Parse the JSON response from Claude
    let parsedResponse;
    try {
      // Try to extract JSON from the response
      const jsonMatch = textContent.text.match(/\{[\s\S]*\}/);
      if (jsonMatch) {
        parsedResponse = JSON.parse(jsonMatch[0]);
      } else {
        // Fallback if Claude doesn't return JSON
        parsedResponse = {
          recommendations: [],
          message: textContent.text,
        };
      }
    } catch (parseError) {
      // If parsing fails, return a default response
      parsedResponse = {
        recommendations: [],
        message: textContent.text,
      };
    }

    return NextResponse.json(parsedResponse);
  } catch (error) {
    console.error('Error calling Anthropic API:', error);
    return NextResponse.json(
      { error: 'Failed to get recommendations' },
      { status: 500 }
    );
  }
}
